/******************************************************************************
* Copyright (c) 2013 Potential Ventures Ltd
* All rights reserved.
*
* Redistribution and use in source and binary forms, with or without
* modification, are permitted provided that the following conditions are met:
*    * Redistributions of source code must retain the above copyright
*      notice, this list of conditions and the following disclaimer.
*    * Redistributions in binary form must reproduce the above copyright
*      notice, this list of conditions and the following disclaimer in the
*      documentation and/or other materials provided with the distribution.
*    * Neither the name of Potential Ventures Ltd nor the
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


#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>

#include "gpi.h"
#include "gpi_logging.h"
#include <vpi_user.h>

// Handle related functions
gpi_sim_hdl gpi_get_root_handle()
{
    FENTER
    vpiHandle root;
    vpiHandle iterator;

    // vpi_iterate with a ref of NULL returns the top level module
    iterator = vpi_iterate(vpiModule, NULL);
    root = vpi_scan(iterator);

    // Need to free the iterator if it didn't return NULL
    if (root != NULL && !vpi_free_object(iterator)) {
        LOG_WARN("VPI: Attempting to free root iterator failed!");
    }
    FEXIT
    return (gpi_sim_hdl)root;
}

gpi_sim_hdl gpi_get_handle_by_name(const char *name, gpi_sim_hdl parent)
{
    FENTER
    gpi_sim_hdl rv;
    int len;
    char *buff;
    if (name)
        len = strlen(name) + 1;

    buff = (char *)malloc(len);
    if (buff== NULL) {
        LOG_CRITICAL("VPI: Attempting allocate string buffer failed!");
        return;
    }

    strncpy(buff, name, len);
    rv = (gpi_sim_hdl)vpi_handle_by_name(buff, (vpiHandle)parent);
    free(buff);
    FEXIT
    return rv;

}


void gpi_sim_end()
{
    vpi_control(vpiFinish);
}

// double gpi_get_sim_time()
void gpi_get_sim_time(uint32_t *high, uint32_t *low)
{
//     FENTERD
    s_vpi_time vpi_time_s;
    vpi_time_s.type = vpiSimTime;//vpiScaledRealTime;        //vpiSimTime;
    vpi_get_time(NULL, &vpi_time_s);
//     FEXIT
//     return vpi_time_s.real;
    *high = vpi_time_s.high;
    *low = vpi_time_s.low;
}

// Value related functions
void gpi_set_signal_value_int(gpi_sim_hdl gpi_hdl, int value)
{
    FENTER
    s_vpi_value value_s;
    p_vpi_value value_p = &value_s;

    value_p->value.integer = value;
    value_p->format = vpiIntVal;

//  *  vpiNoDelay -- Set the value immediately. The p_vpi_time parameter
//  *      may be NULL, in this case. This is like a blocking assignment
//  *      in behavioral code.
    vpi_put_value((vpiHandle)gpi_hdl, value_p, NULL, vpiNoDelay);

    FEXIT
}

void gpi_set_signal_value_str(gpi_sim_hdl gpi_hdl, const char *str)
{
    FENTER
    s_vpi_value value_s;
    p_vpi_value value_p = &value_s;

    int len;
    char *buff;
    if (str)
        len = strlen(str) + 1;

    buff = (char *)malloc(len);
    if (buff== NULL) {
        LOG_CRITICAL("VPI: Attempting allocate string buffer failed!");
        return;
    }

    strncpy(buff, str, len);

    value_p->value.str = buff;
    value_p->format = vpiBinStrVal;

//  *  vpiNoDelay -- Set the value immediately. The p_vpi_time parameter
//  *      may be NULL, in this case. This is like a blocking assignment
//  *      in behavioral code.
    vpi_put_value((vpiHandle)gpi_hdl, value_p, NULL, vpiNoDelay);

    free(buff);
    FEXIT
}






static char *gpi_copy_name(const char *name)
{
    int len;
    char *result;

    if (name)
        len = strlen(name) + 1;
    else {
        LOG_CRITICAL("NULL came back from VPI\n");
        len = 20;
    }

    result = (char *)malloc(len);
    if (result == NULL) {
        LOG_CRITICAL("VPI: Attempting allocate string buffer failed!");
        return NULL;
    }

    snprintf(result, len, "%s\0", name ? name : "UNKNOWN");

    return result;
}


char *gpi_get_signal_value_binstr(gpi_sim_hdl gpi_hdl)
{
    FENTER
    s_vpi_value value_s = {vpiBinStrVal};
    p_vpi_value value_p = &value_s;

    vpi_get_value((vpiHandle)gpi_hdl, value_p);

    char *result = gpi_copy_name(value_p->value.str);
    FEXIT
    return result;
}

char *gpi_get_signal_name_str(gpi_sim_hdl gpi_hdl)
{
    FENTER
    const char *name = vpi_get_str(vpiFullName, (vpiHandle)gpi_hdl);
    char *result = gpi_copy_name(name);
    FEXIT
    return result;
}

char *gpi_get_signal_type_str(gpi_sim_hdl gpi_hdl)
{
    FENTER
    const char *name = vpi_get_str(vpiType, (vpiHandle)gpi_hdl);
    char *result = gpi_copy_name(name);
    FEXIT
    return result;
}


// Callback related functions

// callback user data used for VPI callbacks
// (mostly just a thin wrapper around the gpi_callback)
typedef struct t_vpi_cb_user_data {
    void *gpi_cb_data;
    int (*gpi_function)(void *);
    int (*gpi_cleanup)(struct t_vpi_cb_user_data *);
    vpiHandle cb_hdl;
    s_vpi_value  cb_value;
} s_vpi_cb_user_data, *p_vpi_cb_user_data;


PLI_INT32 handle_vpi_callback(p_cb_data cb_data)
{
    FENTER
    int rv = 0;

    p_vpi_cb_user_data user_data;
    user_data = (p_vpi_cb_user_data)cb_data->user_data;

    rv = user_data->gpi_function(user_data->gpi_cb_data);

    // Call destuctor
    if (user_data->gpi_cleanup)
        user_data->gpi_cleanup(user_data);

    FEXIT
    return rv;
};

// remove a callback without freeing the user data
// (called by callback to clean up)
// vpi_get_cb_info could be used to free user data if
// the callback hasn't fired...
int gpi_deregister_callback(gpi_cb_hdl gpi_hdl)
{
    FENTER
    // This destroys them memory allocated for the handle
    PLI_INT32 rc = vpi_remove_cb((vpiHandle)gpi_hdl);
    FEXIT
    return rc;
}

// Call when the handle relates to a one time callback
// No need to call vpi_deregister_cb as the sim will
// do this but do need to destroy the handle
static int gpi_free_one_time(p_vpi_cb_user_data user_data)
{
    FENTER
    PLI_INT32 rc;
    vpiHandle cb_hdl = user_data->cb_hdl;
    if (!cb_hdl) {
        LOG_ERR("VPI: %s passed a NULL pointer\n", __func__);
        exit(1);
    }

    rc = vpi_free_object(cb_hdl);
    free(user_data);
    FEXIT
    return rc;
}

// Call when the handle relates to recurring callback
// Unregister must be called when not needed and this
// will clean all memory allocated by the sim
static int gpi_free_recurring(p_vpi_cb_user_data user_data)
{
    FENTER
    PLI_INT32 rc;
    vpiHandle cb_hdl = user_data->cb_hdl;
    if (!cb_hdl) {
        LOG_ERR("VPI: %s passed a NULL pointer\n", __func__);
        exit(1);
    }

    rc = vpi_remove_cb(cb_hdl);
    free(user_data);
    FEXIT
    return rc;
}

gpi_cb_hdl gpi_register_value_change_callback(int (*gpi_function)(void *), void *gpi_cb_data, gpi_sim_hdl gpi_hdl)
{
    FENTER
    s_cb_data cb_data_s;
    s_vpi_time vpi_time_s;
    s_vpi_value  vpi_value_s;
    p_vpi_cb_user_data user_data;

    // Freed when callback fires or the callback is deregistered
    user_data = (p_vpi_cb_user_data)malloc(sizeof(s_vpi_cb_user_data));
    if (user_data == NULL) {
        LOG_WARN("VPI: Attempting allocate user_data for %s failed!", __func__);
    }

    user_data->gpi_cb_data = gpi_cb_data;
    user_data->gpi_function = gpi_function;
    user_data->gpi_cleanup = gpi_free_recurring;

    vpi_time_s.type = vpiSuppressTime;
    vpi_value_s.format = vpiIntVal;

    cb_data_s.reason    = cbValueChange;
    cb_data_s.cb_rtn    = handle_vpi_callback;
    cb_data_s.obj       = (vpiHandle)gpi_hdl;
    cb_data_s.time      = &vpi_time_s;
    cb_data_s.value     = &user_data->cb_value;
    cb_data_s.user_data = (char *)user_data;

    user_data->cb_hdl = vpi_register_cb(&cb_data_s);
    FEXIT

    return (gpi_cb_hdl)user_data->cb_hdl;
}


gpi_cb_hdl gpi_register_readonly_callback(int (*gpi_function)(void *), void *gpi_cb_data)
{
    FENTER
    s_cb_data cb_data_s;
    s_vpi_time vpi_time_s;
    p_vpi_cb_user_data user_data;

    // Freed when callback fires or the callback is deregistered
    user_data = (p_vpi_cb_user_data)malloc(sizeof(s_vpi_cb_user_data));
    if (user_data == NULL) {
        LOG_WARN("VPI: Attempting allocate user_data for %s failed!", __func__);
    }

    user_data->gpi_cb_data = gpi_cb_data;
    user_data->gpi_function = gpi_function;
    user_data->gpi_cleanup = gpi_free_one_time;

    vpi_time_s.type = vpiSimTime;
    vpi_time_s.high = 0;
    vpi_time_s.low = 0;

    cb_data_s.reason    = cbReadOnlySynch;
    cb_data_s.cb_rtn    = handle_vpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = &vpi_time_s;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)user_data;

    user_data->cb_hdl = vpi_register_cb(&cb_data_s);

    FEXIT
    return (gpi_cb_hdl)user_data->cb_hdl;
}

gpi_cb_hdl gpi_register_readwrite_callback(int (*gpi_function)(void *), void *gpi_cb_data)
{
    FENTER
    s_cb_data cb_data_s;
    s_vpi_time vpi_time_s;
    p_vpi_cb_user_data user_data;

    // Freed when callback fires or the callback is deregistered
    user_data = (p_vpi_cb_user_data)malloc(sizeof(s_vpi_cb_user_data));
    if (user_data == NULL) {
        LOG_WARN("VPI: Attempting allocate user_data for %s failed!", __func__);
    }

    user_data->gpi_cb_data = gpi_cb_data;
    user_data->gpi_function = gpi_function;
    user_data->gpi_cleanup = gpi_free_one_time;

    vpi_time_s.type = vpiSimTime;
    vpi_time_s.high = 0;
    vpi_time_s.low = 0;

    cb_data_s.reason    = cbReadWriteSynch;
    cb_data_s.cb_rtn    = handle_vpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = &vpi_time_s;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)user_data;

    user_data->cb_hdl = vpi_register_cb(&cb_data_s);

    FEXIT
    return (gpi_cb_hdl)user_data->cb_hdl;
}

gpi_cb_hdl gpi_register_nexttime_callback(int (*gpi_function)(void *), void *gpi_cb_data)
{
    FENTER
    s_cb_data cb_data_s;
    s_vpi_time vpi_time_s;
    p_vpi_cb_user_data user_data;

    // Freed when callback fires or the callback is deregistered
    user_data = (p_vpi_cb_user_data)malloc(sizeof(s_vpi_cb_user_data));
    if (user_data == NULL) {
        LOG_WARN("VPI: Attempting allocate user_data for %s failed!", __func__);
    }

    user_data->gpi_cb_data = gpi_cb_data;
    user_data->gpi_function = gpi_function;
    user_data->gpi_cleanup = gpi_free_one_time;

    vpi_time_s.type = vpiSimTime;
    vpi_time_s.high = 0;
    vpi_time_s.low = 0;

    cb_data_s.reason    = cbNextSimTime;
    cb_data_s.cb_rtn    = handle_vpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = &vpi_time_s;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)user_data;

    user_data->cb_hdl = vpi_register_cb(&cb_data_s);

    FEXIT
    return (gpi_cb_hdl)user_data->cb_hdl;
}

gpi_cb_hdl gpi_register_timed_callback(int (*gpi_function)(void *), void *gpi_cb_data, uint64_t time_ps)
{
    FENTER
    s_cb_data cb_data_s;
    s_vpi_time vpi_time_s;
    p_vpi_cb_user_data user_data;

    // Freed when callback fires or the callback is deregistered
    user_data = (p_vpi_cb_user_data)malloc(sizeof(s_vpi_cb_user_data));
    if (user_data == NULL) {
        LOG_WARN("VPI: Attempting allocate user_data for %s failed!", __func__);
    }

    user_data->gpi_cb_data = gpi_cb_data;
    user_data->gpi_function = gpi_function;
    user_data->gpi_cleanup = gpi_free_one_time;

    vpi_time_s.type = vpiSimTime;
    vpi_time_s.high = (PLI_UINT32)(time_ps>>32);
    vpi_time_s.low  = (PLI_UINT32)(time_ps);

    cb_data_s.reason    = cbAfterDelay;
    cb_data_s.cb_rtn    = handle_vpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = &vpi_time_s;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)user_data;

    user_data->cb_hdl = vpi_register_cb(&cb_data_s);
    FEXIT

    return (gpi_cb_hdl)user_data->cb_hdl;
}

gpi_cb_hdl gpi_register_sim_start_callback(int (*gpi_function)(void *), void *gpi_cb_data)
{
    FENTER

    p_vpi_cb_user_data user_data;
    s_cb_data cb_data_s;

    // Freed when callback fires or the callback is deregistered
    user_data = (p_vpi_cb_user_data)malloc(sizeof(s_vpi_cb_user_data));
    if (user_data == NULL) {
        LOG_WARN("VPI: Attempting allocate user_data for %s failed!", __func__);
    }

    user_data->gpi_cb_data = gpi_cb_data;
    user_data->gpi_function = gpi_function;
    user_data->gpi_cleanup = gpi_free_one_time;

    cb_data_s.reason    = cbStartOfSimulation;
    cb_data_s.cb_rtn    = handle_vpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = NULL;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)user_data;

    user_data->cb_hdl = vpi_register_cb(&cb_data_s);
    FEXIT
    return (gpi_cb_hdl)user_data->cb_hdl;

}

gpi_cb_hdl gpi_register_sim_end_callback(int (*gpi_function)(void *), void *gpi_cb_data)
{
    FENTER

    p_vpi_cb_user_data user_data;
    s_cb_data cb_data_s;

    // Freed when callback fires or the callback is deregistered
    user_data = (p_vpi_cb_user_data)malloc(sizeof(s_vpi_cb_user_data));
    if (user_data == NULL) {
        LOG_WARN("VPI: Attempting allocate user_data for %s failed!", __func__);
    }

    user_data->gpi_cb_data = gpi_cb_data;
    user_data->gpi_function = gpi_function;
    user_data->gpi_cleanup = gpi_free_one_time;

    cb_data_s.reason    = cbEndOfSimulation;
    cb_data_s.cb_rtn    = handle_vpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = NULL;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)user_data;

    user_data->cb_hdl = vpi_register_cb(&cb_data_s);
    FEXIT
    return (gpi_cb_hdl)user_data->cb_hdl;

}

int gpi_clock_handler(void *clock)
{
    gpi_clock_hdl hdl = (gpi_clock_hdl)clock;

    if (hdl->exit || (hdl->max_cycles == hdl->curr_cycle))
        return;

    hdl->value = !hdl->value;
    gpi_set_signal_value_int(hdl->sim_hdl, hdl->value);
    gpi_cb_hdl edge = gpi_register_timed_callback(gpi_clock_handler, hdl, hdl->period);
    hdl->cb_hdl = edge;
    hdl->curr_cycle++;
}

gpi_clock_hdl gpi_clock_register(gpi_sim_hdl sim_hdl, int period, unsigned int cycles)
{
    FENTER

    gpi_clock_hdl hdl = malloc(sizeof(gpi_clock_t));
    if (!hdl)
        LOG_WARN("Unable to allocate memory");

    hdl->period = period;
    hdl->value = 0;
    hdl->sim_hdl = sim_hdl;
    hdl->exit = false;
    hdl->max_cycles = cycles;
    hdl->curr_cycle = 0;

    gpi_set_signal_value_int(hdl->sim_hdl, hdl->value);
    gpi_cb_hdl edge = gpi_register_timed_callback(gpi_clock_handler, hdl, hdl->period);
    hdl->cb_hdl = edge;

    FEXIT
    return hdl;
}

void gpi_clock_unregister(gpi_clock_hdl clock)
{
    clock->exit = true;
}
