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

#define MAX_IMPLS 5

typedef struct impls {
    gpi_impl_tbl tbl;
    int type;
} r_impl;

static r_impl registed_impls[MAX_IMPLS] = {{NULL,0},};

#define IMPL_ROOT   registed_impls[0].tbl

static inline void set_user_data(gpi_sim_hdl hdl, int (*gpi_function)(void*), void *data)
{
    gpi_cb_hdl gpi_user_data = gpi_container_of(hdl, gpi_cb_hdl_t, hdl);

    gpi_user_data->gpi_cb_data = data;
    gpi_user_data->gpi_function = gpi_function;
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
    IMPL_ROOT->sim_end();
}

void gpi_embed_init_python(void)
{
    embed_init_python();
}

void gpi_get_sim_time(uint32_t *high, uint32_t *low)
{
    IMPL_ROOT->get_sim_time(high, low);
}

gpi_sim_hdl gpi_get_root_handle(const char *name)
{
    return IMPL_ROOT->get_root_handle(name);
}

gpi_sim_hdl gpi_get_handle_by_name(const char *name, gpi_sim_hdl parent)
{
    return IMPL_ROOT->get_handle_by_name(name, parent);
}

gpi_sim_hdl gpi_get_handle_by_index(gpi_sim_hdl parent, uint32_t index)
{
    return IMPL_ROOT->get_handle_by_index(parent, index);
}

gpi_iterator_hdl gpi_iterate(uint32_t type, gpi_sim_hdl base)
{
    return IMPL_ROOT->iterate_handle(type, base);;
}

gpi_sim_hdl gpi_next(gpi_iterator_hdl iterator)
{
    return IMPL_ROOT->next_handle(iterator);
}

char *gpi_get_signal_value_binstr(gpi_sim_hdl gpi_hdl)
{
    return IMPL_ROOT->get_signal_value_binstr(gpi_hdl);
}

char *gpi_get_signal_name_str(gpi_sim_hdl gpi_hdl)
{
    return IMPL_ROOT->get_signal_name_str(gpi_hdl);
}

char *gpi_get_signal_type_str(gpi_sim_hdl gpi_hdl)
{
    return IMPL_ROOT->get_signal_type_str(gpi_hdl);
}

void gpi_set_signal_value_int(gpi_sim_hdl gpi_hdl, int value)
{
    IMPL_ROOT->set_signal_value_int(gpi_hdl, value);
}

void gpi_set_signal_value_str(gpi_sim_hdl gpi_hdl, const char *str)
{
    IMPL_ROOT->set_signal_value_str(gpi_hdl, str);
}

void *gpi_get_callback_data(gpi_sim_hdl gpi_hdl)
{
    return IMPL_ROOT->get_callback_data(gpi_hdl);
}

int gpi_register_timed_callback(gpi_sim_hdl hdl,
                                int (*gpi_function)(void *),
                                void *gpi_cb_data, uint64_t time_ps)
{
    set_user_data(hdl, gpi_function, gpi_cb_data);
    return IMPL_ROOT->register_timed_callback(hdl, gpi_function, gpi_cb_data, time_ps);
}

int gpi_register_value_change_callback(gpi_sim_hdl hdl,
                                       int (*gpi_function)(void *),
                                       void *gpi_cb_data, gpi_sim_hdl gpi_hdl)
{
    set_user_data(hdl, gpi_function, gpi_cb_data);
    return IMPL_ROOT->register_value_change_callback(hdl, gpi_function, gpi_cb_data, gpi_hdl);
}

int gpi_register_readonly_callback(gpi_sim_hdl hdl,
                                   int (*gpi_function)(void *),
                                   void *gpi_cb_data)
{
    set_user_data(hdl, gpi_function, gpi_cb_data);
    return IMPL_ROOT->register_readonly_callback(hdl, gpi_function, gpi_cb_data);
}

int gpi_register_nexttime_callback(gpi_sim_hdl hdl,
                                   int (*gpi_function)(void *),
                                   void *gpi_cb_data)
{
    set_user_data(hdl, gpi_function, gpi_cb_data);
    return IMPL_ROOT->register_nexttime_callback(hdl, gpi_function, gpi_cb_data);
}

int gpi_register_readwrite_callback(gpi_sim_hdl hdl,
                                    int (*gpi_function)(void *),
                                    void *gpi_cb_data)
{
    set_user_data(hdl, gpi_function, gpi_cb_data);
    return IMPL_ROOT->register_readwrite_callback(hdl, gpi_function, gpi_cb_data);
}

void gpi_deregister_callback(gpi_sim_hdl hdl)
{
    IMPL_ROOT->deregister_callback(hdl);
}

void gpi_handle_callback(gpi_sim_hdl hdl)
{
    gpi_cb_hdl cb_hdl = gpi_container_of(hdl, gpi_cb_hdl_t, hdl);
    cb_hdl->gpi_function(cb_hdl->gpi_cb_data);
}

/* Callback handles are abstracted to the implementation layer since
   they may need to have some state stored on a per handle basis. 
*/
gpi_sim_hdl gpi_create_cb_handle(void)
{
    gpi_cb_hdl ret = NULL;

    ret = IMPL_ROOT->create_cb_handle();
    if (!ret) {
        LOG_CRITICAL("GPI: Attempting allocate user_data failed!");
    }

    return &ret->hdl; 
}

void gpi_free_cb_handle(gpi_sim_hdl hdl)
{
    gpi_cb_hdl cb_hdl = gpi_container_of(hdl, gpi_cb_hdl_t, hdl);
    IMPL_ROOT->destroy_cb_handle(cb_hdl);
}


/* This needs to be filled with the pointer to the table */
gpi_sim_hdl gpi_create_handle(void)
{
    gpi_sim_hdl new_hdl = calloc(1, sizeof(*new_hdl));
    if (!new_hdl) {
        LOG_CRITICAL("GPI: Could not allocate handle");
        exit(1);
    }

    return new_hdl;
}

void gpi_free_handle(gpi_sim_hdl hdl)
{
    free(hdl);
}

int gpi_register_impl(gpi_impl_tbl func_tbl, int type)
{
    int idx;
    for (idx = 0; idx < MAX_IMPLS; idx++) {
        if (!registed_impls[idx].tbl) {
            /* TODO
             * check that the pointers are set and error if not
             */
            registed_impls[idx].tbl = func_tbl;
            registed_impls[idx].type = type;
        }
    }
    return 0;
}

char *gpi_copy_name(const char *name)
{
    int len;
    char *result;
    const char null[] = "NULL";

    if (name)
        len = strlen(name) + 1;
    else {
        LOG_CRITICAL("GPI: attempt to use NULL from impl");
        len = strlen(null);
        name = null;
    }

    result = (char *)malloc(len);
    if (result == NULL) {
        LOG_CRITICAL("GPI: Attempting allocate string buffer failed!");
        len = strlen(null);
        name = null;
    }

    snprintf(result, len, "%s", name);

    return result;
}

/* TODO
    Each of the top level calls then needs to call into a function
    table pointer to do the actual implementation. This can be on a per
    handle basis.
*/
