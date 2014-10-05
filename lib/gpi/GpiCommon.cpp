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
#include <vector>

using namespace std;

template<class To, class Ti>
inline To sim_to_hdl(Ti input)
{
    To result = reinterpret_cast<To>(input);
    if (!result) {
        LOG_CRITICAL("GPI: Handle passed down is not valid gpi_sim_hdl");
        exit(1);
    }

    return result;
}

static vector<GpiImplInterface*> registered_impls;

int gpi_register_impl(GpiImplInterface *func_tbl)
{
    registered_impls.push_back(func_tbl);
    return 0;
}

void gpi_embed_init(gpi_sim_info_t *info)
{
    embed_sim_init(info);
}

void gpi_embed_end(void)
{
    embed_sim_event(SIM_FAIL, "Simulator shutdown prematurely");
}

void gpi_sim_end(void)
{
    registered_impls[0]->sim_end();
}

void gpi_embed_init_python(void)
{
    embed_init_python();
}

void gpi_get_sim_time(uint32_t *high, uint32_t *low)
{
    registered_impls[0]->get_sim_time(high, low);
}

gpi_sim_hdl gpi_get_root_handle(const char *name)
{
    /* May need to look over all the implementations that are registered
       to find this handle */
    vector<GpiImplInterface*>::iterator iter;

    GpiObjHdl *hdl;

    for (iter = registered_impls.begin();
         iter != registered_impls.end();
         iter++) {
        if ((hdl = (*iter)->get_root_handle(name))) {
            return (void*)hdl;
        }
    }
    return NULL;
}

gpi_sim_hdl gpi_get_handle_by_name(const char *name, gpi_sim_hdl parent)
{
#if 0
    vector<GpiImplInterface*>::iterator iter;

    GpiObjHdl *hdl;
    GpiObjHdl *base = sim_to_hdl<GpiObjHdl>(parent);


    /* Either want this or use the parent */
    for (iter = registered_impls.begin();
         iter != registered_impls.end();
         iter++) {
        LOG_WARN("Quering impl %s", (*iter)->get_name());
        if ((hdl = (*iter)->get_handle_by_name(name, base))) {
            return (void*)hdl;
        }
    }
    hdl = base->m_impl->get_handle_by_name(name, base);
    return (void*)hdl;
#endif
    return NULL;
}

gpi_sim_hdl gpi_get_handle_by_index(gpi_sim_hdl parent, uint32_t index)
{
#if 0
    /* Either want this or use the parent */
    GpiObjHdl *obj_hdl = sim_to_hdl<GpiObjHdl*>(parent);
    return (void*)obj_hdl->m_impl->get_handle_by_index(obj_hdl, index);
#endif
    return NULL;
}

gpi_iterator_hdl gpi_iterate(uint32_t type, gpi_sim_hdl base)
{
#if 0
    GpiObjHdl *obj_hdl = sim_to_hdl<GpiObjHdl*>(base);
    GpiIterator *iter = obj_hdl->m_impl->iterate_handle(type, obj_hdl);
    if (!iter) {
        return NULL;
    }
    iter->parent = obj_hdl;
    return (gpi_iterator_hdl)iter;
#endif
    return NULL;
}

gpi_sim_hdl gpi_next(gpi_iterator_hdl iterator)
{
    GpiIterator *iter = sim_to_hdl<GpiIterator*>(iterator);
    return (gpi_sim_hdl)iter->parent->next_handle(iter);
}

const char *gpi_get_signal_value_binstr(gpi_sim_hdl sig_hdl)
{
    GpiSignalObjHdl *obj_hdl = sim_to_hdl<GpiSignalObjHdl*>(sig_hdl);
    return obj_hdl->get_signal_value_binstr();
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

void gpi_set_signal_value_int(gpi_sim_hdl sig_hdl, int value)
{
    GpiSignalObjHdl *obj_hdl = sim_to_hdl<GpiSignalObjHdl*>(sig_hdl);
    obj_hdl->set_signal_value(value);
}

void gpi_set_signal_value_str(gpi_sim_hdl sig_hdl, const char *str)
{
    GpiSignalObjHdl *obj_hdl = sim_to_hdl<GpiSignalObjHdl*>(sig_hdl);
    obj_hdl->set_signal_value(str);
}

gpi_sim_hdl gpi_register_value_change_callback(const int (*gpi_function)(const void *),
                                               void *gpi_cb_data,
                                               gpi_sim_hdl sig_hdl,
                                               int rising)
{
    #if 0
    GpiObjHdl *obj_hdl = sim_to_hdl<GpiObjHdl*>(sig_hdl);

    /* Do something based on int & GPI_RISING | GPI_FALLING */
    GpiCbHdl *gpi_hdl = obj_hdl->value_change_cb();
    if (!gpi_hdl) {
        LOG_ERROR("Failed to register a value change callback");
        return NULL;
    }

    gpi_hdl->set_user_data(gpi_function, gpi_cb_data);
    return (gpi_sim_hdl)gpi_hdl;
    #endif
    return NULL;
}

/* It should not matter which implementation we use for this so just pick the first
   one */
gpi_sim_hdl gpi_register_timed_callback(const int (*gpi_function)(const void *),
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
gpi_sim_hdl gpi_register_readonly_callback(const int (*gpi_function)(const void *),
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

gpi_sim_hdl gpi_register_nexttime_callback(const int (*gpi_function)(const void *),
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
gpi_sim_hdl gpi_register_readwrite_callback(const int (*gpi_function)(const void *),
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

gpi_sim_hdl gpi_create_clock(gpi_sim_hdl *clk_signal, const int period)
{
    GpiObjHdl *clk_hdl = sim_to_hdl<GpiObjHdl*>(clk_signal);
    GpiClockHdl *clock = new GpiClockHdl(clk_hdl);
    clock->start_clock(period);
    return (gpi_sim_hdl)clock;
}

void gpi_stop_clock(gpi_sim_hdl *clk_object)
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

void gpi_free_handle(gpi_sim_hdl hdl)
{
    GpiObjHdl *obj = sim_to_hdl<GpiObjHdl*>(hdl);
    delete(obj);
}

GpiImplInterface::~GpiImplInterface() { }
GpiImplInterface::GpiImplInterface(const std::string& name) : m_name(name) { }
const char* GpiImplInterface::get_name_c(void) {
    return m_name.c_str();
}
const string& GpiImplInterface::get_name_s(void) {
    return m_name;
}