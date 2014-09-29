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

static inline gpi_cb_hdl * sim_to_cbhdl(gpi_sim_hdl hdl, bool fatal)
{
    gpi_cb_hdl *cb_hdl = reinterpret_cast<gpi_cb_hdl*>(hdl);
    if (!cb_hdl) {
        LOG_CRITICAL("GPI: Handle passed down is not valid gpi_sim_hdl");
        if (fatal)
            exit(1);
    }
    return cb_hdl;
}

static inline gpi_obj_hdl * sim_to_objhdl(gpi_sim_hdl hdl, bool fatal)
{
    gpi_obj_hdl *obj_hdl = reinterpret_cast<gpi_obj_hdl*>(hdl);
    if (!obj_hdl) {
        LOG_CRITICAL("GPI: Handle passed down is not valid gpi_onj_hdl");
        if (fatal)
            exit(1);
    }
    return obj_hdl;
}

static inline gpi_iterator * sim_to_iterhdl(gpi_sim_hdl hdl, bool fatal)
{
    gpi_iterator *iter_hdl = reinterpret_cast<gpi_iterator*>(hdl);
    if (!iter_hdl) {
        LOG_CRITICAL("GPI: Handle passed down is not valid gpi_iterator");
        if (fatal)
            exit(1);
    }
    return iter_hdl;
}

static vector<gpi_impl_interface*> registered_impls;

int gpi_register_impl(gpi_impl_interface *func_tbl)
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
    vector<gpi_impl_interface*>::iterator iter;

    gpi_obj_hdl *hdl;

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
    vector<gpi_impl_interface*>::iterator iter;

    gpi_obj_hdl *hdl;
    gpi_obj_hdl *base = sim_to_objhdl(parent, true);

    /* Either want this or use the parent */
    for (iter = registered_impls.begin();
         iter != registered_impls.end();
         iter++) {
        if ((hdl = (*iter)->get_handle_by_name(name, base))) {
            return (void*)hdl;
        }
    }
#if 0
    hdl = base->m_impl->get_handle_by_name(name, base);
    return (void*)hdl;
#endif
    return NULL;
}

gpi_sim_hdl gpi_get_handle_by_index(gpi_sim_hdl parent, uint32_t index)
{
    /* Either want this or use the parent */
    gpi_obj_hdl *obj_hdl = sim_to_objhdl(parent, false);
    return (void*)obj_hdl->m_impl->get_handle_by_index(obj_hdl, index);
}

gpi_iterator_hdl gpi_iterate(uint32_t type, gpi_sim_hdl base)
{
    gpi_obj_hdl *obj_hdl = sim_to_objhdl(base, false);
    gpi_iterator *iter = obj_hdl->m_impl->iterate_handle(type, obj_hdl);
    if (!iter) {
        return NULL;
    }
    iter->parent = obj_hdl;
    return (void*)iter;
}

gpi_sim_hdl gpi_next(gpi_iterator_hdl iterator)
{
    gpi_iterator *iter = sim_to_iterhdl(iterator, false);
    return (void*)iter->parent->m_impl->next_handle(iter);
}

char *gpi_get_signal_value_binstr(gpi_sim_hdl sig_hdl)
{
    gpi_obj_hdl *obj_hdl = sim_to_objhdl(sig_hdl, false);
    return obj_hdl->m_impl->get_signal_value_binstr(obj_hdl);
}

char *gpi_get_signal_name_str(gpi_sim_hdl sig_hdl)
{
    gpi_obj_hdl *obj_hdl = sim_to_objhdl(sig_hdl, false);
    return obj_hdl->m_impl->get_signal_name_str(obj_hdl);
}

char *gpi_get_signal_type_str(gpi_sim_hdl sig_hdl)
{
    gpi_obj_hdl *obj_hdl = sim_to_objhdl(sig_hdl, false);
    return obj_hdl->m_impl->get_signal_type_str(obj_hdl);
}

void gpi_set_signal_value_int(gpi_sim_hdl sig_hdl, int value)
{
    gpi_obj_hdl *obj_hdl = sim_to_objhdl(sig_hdl, false);
    obj_hdl->m_impl->set_signal_value_int(obj_hdl, value);
}

void gpi_set_signal_value_str(gpi_sim_hdl sig_hdl, const char *str)
{
    gpi_obj_hdl *obj_hdl = sim_to_objhdl(sig_hdl, false);
    obj_hdl->m_impl->set_signal_value_str(obj_hdl, str);
}

void *gpi_get_callback_data(gpi_sim_hdl sim_hdl)
{
    gpi_cb_hdl *cb_hdl = sim_to_cbhdl(sim_hdl, false);
    return cb_hdl->get_user_data();
}

gpi_sim_hdl gpi_register_value_change_callback(int (*gpi_function)(void *),
                                               void *gpi_cb_data,
                                               gpi_sim_hdl sig_hdl)
{
    gpi_obj_hdl *obj_hdl = sim_to_objhdl(sig_hdl, false);
    gpi_cb_hdl *gpi_hdl = obj_hdl->m_impl->register_value_change_callback(obj_hdl);
    if (!gpi_hdl) {
        LOG_ERROR("Failed to register a value change callback");
        return NULL;
    }

    gpi_hdl->set_user_data(gpi_function, gpi_cb_data);
    return (gpi_sim_hdl)gpi_hdl;
}

/* It should not matter which implementation we use for this so just pick the first
   one
*/
gpi_sim_hdl gpi_register_timed_callback(int (*gpi_function)(void *),
                                        void *gpi_cb_data, uint64_t time_ps)
{
    gpi_cb_hdl *gpi_hdl = registered_impls[0]->register_timed_callback(time_ps);
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
gpi_sim_hdl gpi_register_readonly_callback(int (*gpi_function)(void *),
                                           void *gpi_cb_data)
{
    gpi_cb_hdl *gpi_hdl = registered_impls[0]->register_readonly_callback();
    if (!gpi_hdl) {
        LOG_ERROR("Failed to register a readonly callback");
        return NULL;
    }
    
    gpi_hdl->set_user_data(gpi_function, gpi_cb_data);
    return (gpi_sim_hdl)gpi_hdl;
}

gpi_sim_hdl gpi_register_nexttime_callback(int (*gpi_function)(void *),
                                           void *gpi_cb_data)
{
    gpi_cb_hdl *gpi_hdl = registered_impls[0]->register_nexttime_callback();
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
gpi_sim_hdl gpi_register_readwrite_callback(int (*gpi_function)(void *),
                                            void *gpi_cb_data)
{
    gpi_cb_hdl *gpi_hdl = registered_impls[0] ->register_readwrite_callback();
    if (!gpi_hdl) {
        LOG_ERROR("Failed to register a readwrite callback");
        return NULL;
    }
    
    gpi_hdl->set_user_data(gpi_function, gpi_cb_data);
    return (gpi_sim_hdl)gpi_hdl;
}


void gpi_deregister_callback(gpi_sim_hdl hdl)
{
    gpi_cb_hdl *cb_hdl = sim_to_cbhdl(hdl, false);
    cb_hdl->m_impl->deregister_callback(cb_hdl);
}

void gpi_free_handle(gpi_sim_hdl hdl)
{
    gpi_obj_hdl *obj = sim_to_objhdl(hdl, true);
    delete(obj);
}

gpi_impl_interface::~gpi_impl_interface() { }
gpi_impl_interface::gpi_impl_interface(const string& name) : m_name(name) { }