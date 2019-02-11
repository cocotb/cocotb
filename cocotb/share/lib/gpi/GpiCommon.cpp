/******************************************************************************
* Copyright (c) 2013 Potential Ventures Ltd
* Copyright (c) 2013 SolarFlare Communications Inc
* All rights reserved.
*
* Redistribution and use in source and binary forms, with or without
* modification, are permitted provided that the following conditions are met:
*    * Redistributions of source code must retain the above copyright
*      notice, this list of conditions and the following disclaimer.
*    * Redistributions in binary form must reproduce the above copyright
*      notice, this list of conditions and the following disclaimer in the
*      documentation and/or other materials provided with the distribution.
*    * Neither the name of Potential Ventures Ltd,
*       SolarFlare Communications Inc nor the
*      names of its contributors may be used to endorse or promote products
*      derived from this software without specific prior written permission.
*
* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
* ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
* WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
* DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
* DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
* (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
* LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
* ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
* (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
* SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
******************************************************************************/

#include "gpi_priv.h"
#include <cocotb_utils.h>
#include <sys/types.h>
#include <unistd.h>
#include <vector>
#include <map>

using namespace std;

static vector<GpiImplInterface*> registered_impls;

#ifdef SINGLETON_HANDLES

class GpiHandleStore {
public:
    GpiObjHdl * check_and_store(GpiObjHdl *hdl) {
        std::map<std::string, GpiObjHdl*>::iterator it;

        const std::string &name = hdl->get_fullname();

        LOG_DEBUG("Checking %s exists", name.c_str());

        it = handle_map.find(name);
        if (it == handle_map.end()) {
            handle_map[name] = hdl;
            return hdl;
        } else {
            LOG_DEBUG("Found duplicate %s", name.c_str());

            delete hdl;
            return it->second;
        }
    }

    uint64_t handle_count(void) {
        return handle_map.size();
    }

private:
    std::map<std::string, GpiObjHdl*> handle_map;

};

static GpiHandleStore unique_handles;

#define CHECK_AND_STORE(_x) unique_handles.check_and_store(_x)

#else

#define CHECK_AND_STORE(_x) _x

#endif


int gpi_print_registered_impl(void)
{
    vector<GpiImplInterface*>::iterator iter;
    for (iter = registered_impls.begin();
         iter != registered_impls.end();
         iter++)
    {
        LOG_INFO("%s registered", (*iter)->get_name_c());
    }
    return registered_impls.size();
}

int gpi_register_impl(GpiImplInterface *func_tbl)
{
    vector<GpiImplInterface*>::iterator iter;
    for (iter = registered_impls.begin();
         iter != registered_impls.end();
         iter++)
    {
        if ((*iter)->get_name_s() == func_tbl->get_name_s()) {
            LOG_WARN("%s already registered, Check GPI_EXTRA", func_tbl->get_name_c());
            return -1;
        }
    }
    registered_impls.push_back(func_tbl);
    return 0;
}

void gpi_embed_init(gpi_sim_info_t *info)
{
    if (embed_sim_init(info))
        gpi_embed_end();
}

void gpi_embed_end(void)

{
    embed_sim_event(SIM_FAIL, "Simulator shutdown prematurely");
}

void gpi_sim_end(void)
{
    registered_impls[0]->sim_end();
}

void gpi_embed_event(gpi_event_t level, const char *msg)
{
    embed_sim_event(level, msg);
}

static void gpi_load_libs(std::vector<std::string> to_load)
{
#define DOT_LIB_EXT "." xstr(LIB_EXT)
    std::vector<std::string>::iterator iter;

    for (iter = to_load.begin();
         iter != to_load.end();
         iter++)
    {
        void *lib_handle = NULL;
        std::string full_name = "lib" + *iter + DOT_LIB_EXT;
        const char *now_loading = (full_name).c_str();

        lib_handle = utils_dyn_open(now_loading);
        if (!lib_handle) {
            printf("Error loading lib %s\n", now_loading);
            exit(1);
        }
        std::string sym = (*iter) + "_entry_point";
        void *entry_point = utils_dyn_sym(lib_handle, sym.c_str());
        if (!entry_point) {
            printf("Unable to find entry point for %s\n", now_loading);
            exit(1);
        }

        layer_entry_func new_lib_entry = (layer_entry_func)entry_point;
        new_lib_entry();
    }
}

void gpi_load_extra_libs(void)
{
    static bool loading = false;

    if (loading)
        return;

    /* Lets look at what other libs we where asked to load too */
    char *lib_env = getenv("GPI_EXTRA");

    if (lib_env) {
        std::string lib_list = lib_env;
        std::string delim = ":";
        std::vector<std::string> to_load;

        size_t e_pos = 0;
        while (std::string::npos != (e_pos = lib_list.find(delim))) {
            std::string lib = lib_list.substr(0, e_pos);
            lib_list.erase(0, e_pos + delim.length());

            to_load.push_back(lib);
        }
        if (lib_list.length()) {
            to_load.push_back(lib_list);
        }

        loading = true;
        gpi_load_libs(to_load);
    }

    /* Finally embed python */
    embed_init_python();
    gpi_print_registered_impl();
}

void gpi_get_sim_time(uint32_t *high, uint32_t *low)
{
    registered_impls[0]->get_sim_time(high, low);
}

void gpi_get_sim_precision(int32_t *precision)
{
    /* We clamp to sensible values here, 1e-15 min and 1e3 max */
    int32_t val;
    registered_impls[0]->get_sim_precision(&val);
    if (val > 2 )
        val = 2;

    if (val < -15)
        val = -15;

    *precision = val;

}

gpi_sim_hdl gpi_get_root_handle(const char *name)
{
    /* May need to look over all the implementations that are registered
       to find this handle */
    vector<GpiImplInterface*>::iterator iter;

    GpiObjHdl *hdl = NULL;

    LOG_DEBUG("Looking for root handle '%s' over %d impls", name, registered_impls.size());

    for (iter = registered_impls.begin();
         iter != registered_impls.end();
         iter++) {
        if ((hdl = (*iter)->get_root_handle(name))) {
            LOG_DEBUG("Got a Root handle (%s) back from %s",
                hdl->get_name_str(),
                (*iter)->get_name_c());
            break;
        }
    }

    if (hdl)
        return CHECK_AND_STORE(hdl);
    else {
        LOG_ERROR("No root handle found");
        return hdl;
    }
}

static GpiObjHdl* __gpi_get_handle_by_name(GpiObjHdl *parent,
                                           std::string name,
                                           GpiImplInterface *skip_impl)
{
    vector<GpiImplInterface*>::iterator iter;

    GpiObjHdl *hdl = NULL;

    LOG_DEBUG("Searching for %s", name.c_str());

    for (iter = registered_impls.begin();
         iter != registered_impls.end();
         iter++) {

        if (skip_impl && (skip_impl == (*iter))) {
            LOG_DEBUG("Skipping %s impl", (*iter)->get_name_c());
            continue;
        }

        LOG_DEBUG("Checking if %s native though impl %s",
                  name.c_str(),
                  (*iter)->get_name_c());

        /* If the current interface is not the same as the one that we
           are going to query then append the name we are looking for to
           the parent, such as <parent>.name. This is so that it entity can
           be seen discovered even if the parents implementation is not the same
           as the one that we are querying through */

        //std::string &to_query = base->is_this_impl(*iter) ? s_name : fq_name;
        if ((hdl = (*iter)->native_check_create(name, parent))) {
            LOG_DEBUG("Found %s via %s", name.c_str(), (*iter)->get_name_c());
            break;
        }
    }

    if (hdl)
        return CHECK_AND_STORE(hdl);
    else
        return hdl;
}

static GpiObjHdl* __gpi_get_handle_by_raw(GpiObjHdl *parent,
                                          void *raw_hdl,
                                          GpiImplInterface *skip_impl)
{
    vector<GpiImplInterface*>::iterator iter;

    GpiObjHdl *hdl = NULL;

    for (iter = registered_impls.begin();
         iter != registered_impls.end();
         iter++) {

        if (skip_impl && (skip_impl == (*iter))) {
            LOG_DEBUG("Skipping %s impl", (*iter)->get_name_c());
            continue;
        }

        if ((hdl = (*iter)->native_check_create(raw_hdl, parent))) {
            LOG_DEBUG("Found %s via %s", hdl->get_name_str(), (*iter)->get_name_c());
            break;
        }
    }

    if (hdl)
        return CHECK_AND_STORE(hdl);
    else {
        LOG_WARN("Failed to convert a raw handle to valid object via any registered implementation");
        return hdl;
    }
}

gpi_sim_hdl gpi_get_handle_by_name(gpi_sim_hdl parent, const char *name)
{
    std::string s_name = name;
    GpiObjHdl *base = sim_to_hdl<GpiObjHdl*>(parent);
    GpiObjHdl *hdl = __gpi_get_handle_by_name(base, s_name, NULL);
    if (!hdl) {
        LOG_DEBUG("Failed to find a hdl named %s via any registered implementation",
                 name);
    }
    return hdl;
}

gpi_sim_hdl gpi_get_handle_by_index(gpi_sim_hdl parent, int32_t index)
{
    vector<GpiImplInterface*>::iterator iter;

    GpiObjHdl *hdl         = NULL;
    GpiObjHdl *base        = sim_to_hdl<GpiObjHdl*>(parent);
    GpiImplInterface *intf = base->m_impl;

    /* Shouldn't need to iterate over interfaces because indexing into a handle shouldn't
     * cross the interface boundaries.
     *
     * NOTE: IUS's VPI interface returned valid VHDL handles, but then couldn't
     *       use the handle properly.
     */
    LOG_DEBUG("Checking if index %d native though impl %s ", index, intf->get_name_c());
    hdl = intf->native_check_create(index, base);

    if (hdl)
        return CHECK_AND_STORE(hdl);
    else {
        LOG_WARN("Failed to find a hdl at index %d via any registered implementation", index);
        return hdl;
    }
}

gpi_iterator_hdl gpi_iterate(gpi_sim_hdl base, gpi_iterator_sel_t type)
{
    GpiObjHdl *obj_hdl = sim_to_hdl<GpiObjHdl*>(base);
    GpiIterator *iter = obj_hdl->m_impl->iterate_handle(obj_hdl, type);
    if (!iter) {
        return NULL;
    }
    return (gpi_iterator_hdl)iter;
}

gpi_sim_hdl gpi_next(gpi_iterator_hdl iterator)
{
    std::string name;
    GpiIterator *iter = sim_to_hdl<GpiIterator*>(iterator);
    GpiObjHdl *parent = iter->get_parent();

    while (true) {
        GpiObjHdl *next = NULL;
        void *raw_hdl = NULL;
        GpiIterator::Status ret = iter->next_handle(name, &next, &raw_hdl);

        switch (ret) {
            case GpiIterator::NATIVE:
                LOG_DEBUG("Create a native handle");
                return CHECK_AND_STORE(next);
            case GpiIterator::NATIVE_NO_NAME:
                LOG_DEBUG("Unable to fully setup handle, skipping");
                continue;
            case GpiIterator::NOT_NATIVE:
                LOG_DEBUG("Found a name but unable to create via native implementation, trying others");
                next = __gpi_get_handle_by_name(parent, name, iter->m_impl);
                if (next) {
                    return next;
                }
                LOG_WARN("Unable to create %s via any registered implementation", name.c_str());
                continue;
            case GpiIterator::NOT_NATIVE_NO_NAME:
                LOG_DEBUG("Found an object but not accesbile via %s, trying others", iter->m_impl->get_name_c());
                next = __gpi_get_handle_by_raw(parent, raw_hdl, iter->m_impl);
                if (next) {
                    return next;
                }
                continue;
            case GpiIterator::END:
                LOG_DEBUG("Reached end of iterator");
                delete iter;
                return NULL;
        }
    }
}

const char* gpi_get_definition_name(gpi_sim_hdl sig_hdl)
{
    GpiObjHdl *obj_hdl = sim_to_hdl<GpiObjHdl*>(sig_hdl);
    return obj_hdl->get_definition_name();
}

const char* gpi_get_definition_file(gpi_sim_hdl sig_hdl)
{
    GpiObjHdl *obj_hdl = sim_to_hdl<GpiObjHdl*>(sig_hdl);
    return obj_hdl->get_definition_file();
}

const char *gpi_get_signal_value_binstr(gpi_sim_hdl sig_hdl)
{
    GpiSignalObjHdl *obj_hdl = sim_to_hdl<GpiSignalObjHdl*>(sig_hdl);
    return obj_hdl->get_signal_value_binstr();
}

const char *gpi_get_signal_value_str(gpi_sim_hdl sig_hdl)
{
    GpiSignalObjHdl *obj_hdl = sim_to_hdl<GpiSignalObjHdl*>(sig_hdl);
    return obj_hdl->get_signal_value_str();
}

double gpi_get_signal_value_real(gpi_sim_hdl sig_hdl)
{
    GpiSignalObjHdl *obj_hdl = sim_to_hdl<GpiSignalObjHdl*>(sig_hdl);
    return obj_hdl->get_signal_value_real();
}

long gpi_get_signal_value_long(gpi_sim_hdl sig_hdl)
{
    GpiSignalObjHdl *obj_hdl = sim_to_hdl<GpiSignalObjHdl*>(sig_hdl);
    return obj_hdl->get_signal_value_long();
}

const char *gpi_get_signal_name_str(gpi_sim_hdl sig_hdl)
{
    GpiSignalObjHdl *obj_hdl = sim_to_hdl<GpiSignalObjHdl*>(sig_hdl);
    return obj_hdl->get_name_str();
}

const char *gpi_get_signal_type_str(gpi_sim_hdl sig_hdl)
{
    GpiObjHdl *obj_hdl = sim_to_hdl<GpiObjHdl*>(sig_hdl);
    return obj_hdl->get_type_str();
}

gpi_objtype_t gpi_get_object_type(gpi_sim_hdl sig_hdl)
{
    GpiObjHdl *obj_hdl = sim_to_hdl<GpiObjHdl*>(sig_hdl);
    return obj_hdl->get_type();
}

int gpi_is_constant(gpi_sim_hdl sig_hdl)
{
    GpiObjHdl *obj_hdl = sim_to_hdl<GpiObjHdl*>(sig_hdl);
    if (obj_hdl->get_const())
        return 1;
    return 0;
}

int gpi_is_indexable(gpi_sim_hdl sig_hdl)
{
    GpiObjHdl *obj_hdl = sim_to_hdl<GpiObjHdl*>(sig_hdl);
    if (obj_hdl->get_indexable())
        return 1;
    return 0;
}

void gpi_set_signal_value_long(gpi_sim_hdl sig_hdl, long value)
{
    GpiSignalObjHdl *obj_hdl = sim_to_hdl<GpiSignalObjHdl*>(sig_hdl);
    obj_hdl->set_signal_value(value);
}

void gpi_set_signal_value_str(gpi_sim_hdl sig_hdl, const char *str)
{
    std::string value = str;
    GpiSignalObjHdl *obj_hdl = sim_to_hdl<GpiSignalObjHdl*>(sig_hdl);
    obj_hdl->set_signal_value(value);
}

void gpi_set_signal_value_real(gpi_sim_hdl sig_hdl, double value)
{
    GpiSignalObjHdl *obj_hdl = sim_to_hdl<GpiSignalObjHdl*>(sig_hdl);
    obj_hdl->set_signal_value(value);
}

int gpi_get_num_elems(gpi_sim_hdl sig_hdl)
{
    GpiObjHdl *obj_hdl = sim_to_hdl<GpiObjHdl*>(sig_hdl);
    return obj_hdl->get_num_elems();
}

int gpi_get_range_left(gpi_sim_hdl sig_hdl)
{
    GpiObjHdl *obj_hdl = sim_to_hdl<GpiObjHdl*>(sig_hdl);
    return obj_hdl->get_range_left();
}

int gpi_get_range_right(gpi_sim_hdl sig_hdl)
{
    GpiObjHdl *obj_hdl = sim_to_hdl<GpiObjHdl*>(sig_hdl);
    return obj_hdl->get_range_right();
}

gpi_sim_hdl gpi_register_value_change_callback(int (*gpi_function)(const void *),
                                               void *gpi_cb_data,
                                               gpi_sim_hdl sig_hdl,
                                               unsigned int edge)
{

    GpiSignalObjHdl *signal_hdl = sim_to_hdl<GpiSignalObjHdl*>(sig_hdl);

    /* Do something based on int & GPI_RISING | GPI_FALLING */
    GpiCbHdl *gpi_hdl = signal_hdl->value_change_cb(edge);
    if (!gpi_hdl) {
        LOG_ERROR("Failed to register a value change callback");
        return NULL;
    }

    gpi_hdl->set_user_data(gpi_function, gpi_cb_data);
    return (gpi_sim_hdl)gpi_hdl;
}

/* It should not matter which implementation we use for this so just pick the first
   one */
gpi_sim_hdl gpi_register_timed_callback(int (*gpi_function)(const void *),
                                        void *gpi_cb_data, uint64_t time_ps)
{
    GpiCbHdl *gpi_hdl = registered_impls[0]->register_timed_callback(time_ps);
    if (!gpi_hdl) {
        LOG_ERROR("Failed to register a timed callback");
        return NULL;
    }

    gpi_hdl->set_user_data(gpi_function, gpi_cb_data);
    return (gpi_sim_hdl)gpi_hdl;
}

/* It should not matter which implementation we use for this so just pick the first
   one
*/
gpi_sim_hdl gpi_register_readonly_callback(int (*gpi_function)(const void *),
                                           void *gpi_cb_data)
{
    GpiCbHdl *gpi_hdl = registered_impls[0]->register_readonly_callback();
    if (!gpi_hdl) {
        LOG_ERROR("Failed to register a readonly callback");
        return NULL;
    }

    gpi_hdl->set_user_data(gpi_function, gpi_cb_data);
    return (gpi_sim_hdl)gpi_hdl;
}

gpi_sim_hdl gpi_register_nexttime_callback(int (*gpi_function)(const void *),
                                           void *gpi_cb_data)
{
    GpiCbHdl *gpi_hdl = registered_impls[0]->register_nexttime_callback();
    if (!gpi_hdl) {
        LOG_ERROR("Failed to register a nexttime callback");
        return NULL;
    }

    gpi_hdl->set_user_data(gpi_function, gpi_cb_data);
    return (gpi_sim_hdl)gpi_hdl;
}

/* It should not matter which implementation we use for this so just pick the first
   one
*/
gpi_sim_hdl gpi_register_readwrite_callback(int (*gpi_function)(const void *),
                                            void *gpi_cb_data)
{
    GpiCbHdl *gpi_hdl = registered_impls[0] ->register_readwrite_callback();
    if (!gpi_hdl) {
        LOG_ERROR("Failed to register a readwrite callback");
        return NULL;
    }

    gpi_hdl->set_user_data(gpi_function, gpi_cb_data);
    return (gpi_sim_hdl)gpi_hdl;
}

gpi_sim_hdl gpi_create_clock(gpi_sim_hdl clk_signal, const int period)
{
    GpiObjHdl *clk_hdl = sim_to_hdl<GpiObjHdl*>(clk_signal);
    GpiClockHdl *clock = new GpiClockHdl(clk_hdl);
    clock->start_clock(period);
    return (gpi_sim_hdl)clock;
}

void gpi_stop_clock(gpi_sim_hdl clk_object)
{
    GpiClockHdl *clock = sim_to_hdl<GpiClockHdl*>(clk_object);
    clock->stop_clock();
    delete(clock);
}

void gpi_deregister_callback(gpi_sim_hdl hdl)
{
    GpiCbHdl *cb_hdl = sim_to_hdl<GpiCbHdl*>(hdl);
    cb_hdl->m_impl->deregister_callback(cb_hdl);
}

const char* GpiImplInterface::get_name_c(void) {
    return m_name.c_str();
}

const string& GpiImplInterface::get_name_s(void) {
    return m_name;
}
