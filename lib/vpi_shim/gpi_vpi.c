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

#include <gpi.h>
#include <gpi_logging.h>
#include <embed.h>
#include <vpi_user.h>

#define gpi_container_of(_address, _type, _member)  \
        ((_type *)((uintptr_t)(_address) -      \
         (uintptr_t)(&((_type *)0)->_member)))

static gpi_sim_hdl sim_init_cb;
static gpi_sim_hdl sim_finish_cb;

// callback user data used for VPI callbacks
// (mostly just a thin wrapper around the gpi_callback)
typedef struct t_vpi_cb_user_data {
    void *gpi_cb_data;
    int (*gpi_function)(void *);
    int (*gpi_cleanup)(struct t_vpi_cb_user_data *);
    vpiHandle cb_hdl;
    s_vpi_value  cb_value;
    gpi_sim_hdl_t gpi_hdl;
    bool called;
    bool cleared;
} s_vpi_cb_user_data, *p_vpi_cb_user_data;

// Define a type of a clock object
typedef struct gpi_clock_s {
    int period;
    int value;
    unsigned int max_cycles;
    unsigned int curr_cycle;
    bool exit;
    gpi_sim_hdl_t gpi_hdl;  /* Handle to pass back to called */
    gpi_sim_hdl clk_hdl;    /* Handle for signal to operate on */
    gpi_sim_hdl cb_hdl;     /* Handle for the current pending callback */
} gpi_clock_t;

typedef gpi_clock_t *gpi_clock_hdl;

void gpi_free_handle(gpi_sim_hdl gpi_hdl)
{
    free(gpi_hdl);
}

static gpi_sim_hdl gpi_alloc_handle()
{
    gpi_sim_hdl new_hdl = malloc(sizeof(*new_hdl));
    if (!new_hdl) {
        LOG_CRITICAL("VPI: Could not allocate handle\n");
        exit(1);
    }

    return new_hdl;
}

// Handle related functions
gpi_sim_hdl gpi_get_root_handle()
{
    FENTER
    vpiHandle root;
    vpiHandle iterator;
    gpi_sim_hdl rv;

    // vpi_iterate with a ref of NULL returns the top level module
    iterator = vpi_iterate(vpiModule, NULL);
    root = vpi_scan(iterator);

    // Need to free the iterator if it didn't return NULL
    if (root != NULL && !vpi_free_object(iterator)) {
        LOG_WARN("VPI: Attempting to free root iterator failed!");
    }

    rv = gpi_alloc_handle();
    rv->sim_hdl = root;

    FEXIT
    return rv;
}

gpi_sim_hdl gpi_get_handle_by_name(const char *name, gpi_sim_hdl parent)
{
    FENTER
    gpi_sim_hdl rv;
    vpiHandle obj;
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
    obj = vpi_handle_by_name(buff, (vpiHandle)(parent->sim_hdl));
    free(buff);

    rv = gpi_alloc_handle();
    rv->sim_hdl = obj;

    FEXIT
    return rv;
}


// Functions for iterating over entries of a handle
// Returns an iterator handle which can then be used in gpi_next calls
gpi_iterator_hdl gpi_iterate(gpi_sim_hdl base) {
    FENTER

    vpiHandle iterator;

    iterator = vpi_iterate(vpiNet, (vpiHandle)(base->sim_hdl));

    FEXIT
    return (gpi_iterator_hdl)iterator;
}

// Returns NULL when there are no more objects
gpi_sim_hdl gpi_next(gpi_iterator_hdl iterator)
{
    FENTER
    vpiHandle result;
    gpi_sim_hdl rv = gpi_alloc_handle();

    rv->sim_hdl = vpi_scan((vpiHandle) iterator);
    if (!rv->sim_hdl) {
        gpi_free_handle(rv);
        rv = NULL;
    }

//      FIXME do we need to free the iterator handle?
//      Icarus complains about this
//     if (result == NULL) && !vpi_free_object((vpiHandle)iterator)) {
//         LOG_WARN("VPI: Attempting to free iterator failed!");
//     }
    
    FEXIT
    return rv;
}

// double gpi_get_sim_time()
void gpi_get_sim_time(uint32_t *high, uint32_t *low)
{
    s_vpi_time vpi_time_s;
    vpi_time_s.type = vpiSimTime;//vpiScaledRealTime;        //vpiSimTime;
    vpi_get_time(NULL, &vpi_time_s);
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

    /*  vpiNoDelay -- Set the value immediately. The p_vpi_time parameter
     *      may be NULL, in this case. This is like a blocking assignment
     *      in behavioral code.
     */
    vpi_put_value((vpiHandle)(gpi_hdl->sim_hdl), value_p, NULL, vpiNoDelay);

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

    /*  vpiNoDelay -- Set the value immediately. The p_vpi_time parameter
     *      may be NULL, in this case. This is like a blocking assignment
     *      in behavioral code.
     */
    vpi_put_value((vpiHandle)(gpi_hdl->sim_hdl), value_p, NULL, vpiNoDelay);

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

    vpi_get_value((vpiHandle)(gpi_hdl->sim_hdl), value_p);

    char *result = gpi_copy_name(value_p->value.str);
    FEXIT
    return result;
}

char *gpi_get_signal_name_str(gpi_sim_hdl gpi_hdl)
{
    FENTER
    const char *name = vpi_get_str(vpiFullName, (vpiHandle)(gpi_hdl->sim_hdl));
    char *result = gpi_copy_name(name);
    FEXIT
    return result;
}

char *gpi_get_signal_type_str(gpi_sim_hdl gpi_hdl)
{
    FENTER
    const char *name = vpi_get_str(vpiType, (vpiHandle)(gpi_hdl->sim_hdl));
    char *result = gpi_copy_name(name);
    FEXIT
    return result;
}


// Callback related functions

// Ask the attached simulator to return the user pointer
// that was given when the callback was registered
// Useful for operating on the data before the callback
// has fired since we only have the handle in hand
static p_vpi_cb_user_data gpi_get_user_data(gpi_sim_hdl hdl)
{
     p_vpi_cb_user_data user_data;
     s_cb_data cbdata;
     FENTER

     vpi_get_cb_info((vpiHandle)hdl, &cbdata);

     user_data = (p_vpi_cb_user_data)cbdata.user_data;

     FEXIT
     return user_data;
}


int32_t handle_vpi_callback(p_cb_data cb_data)
{
    FENTER
    int rv = 0;

    p_vpi_cb_user_data user_data;
    user_data = (p_vpi_cb_user_data)cb_data->user_data;


    user_data->called = true;
    rv = user_data->gpi_function(user_data->gpi_cb_data);

    // We call into deregister to remove from the connected
    // simulator, the freeing on data will not be done
    // until there is not reference left though

    gpi_deregister_callback(&user_data->gpi_hdl);

    FEXIT
    return rv;
};

// Cleaing up is a bit complex
// 1. We need to remove the callback and
// it's associated handle internally so that
// there is a not a duplicate trigger event
// 2. The user data needs to stay around until
// thre are no more handles to it.
// Thus this function calls into the sim
// to close down if able to. Or if there
// is no internal state it closes down
// the user data.
int gpi_deregister_callback(gpi_sim_hdl gpi_hdl)
{
    p_vpi_cb_user_data user_data;
    FENTER
    // We should be able to user gpi_get_user_data
    // but this is not implemented in ICARUS
    // and gets upset on VCS. So instead we
    // do some pointer magic.

    user_data = gpi_container_of(gpi_hdl, s_vpi_cb_user_data, gpi_hdl);

    if (user_data->cleared) {
        memset(user_data, 0x0, sizeof(*user_data));
        free(user_data);
    } else if (user_data->gpi_cleanup) {
        user_data->gpi_cleanup(user_data);
        user_data->cleared = true;
    }

    FEXIT
    return 1;
}

// Call when the handle relates to a one time callback
// No need to call vpi_deregister_cb as the sim will
// do this but do need to destroy the handle
static int gpi_free_one_time(p_vpi_cb_user_data user_data)
{
    FENTER
    int32_t rc;
    vpiHandle cb_hdl = user_data->cb_hdl;
    if (!cb_hdl) {
        LOG_ERROR("VPI: %s passed a NULL pointer\n", __func__);
        exit(1);
    }

    // If the callback has not been called we also need to call
    // remove as well
    if (!user_data->called)
        rc = vpi_remove_cb(cb_hdl);
    else 
        rc = vpi_free_object(cb_hdl);

    FEXIT
    return 1;
}

// Call when the handle relates to recurring callback
// Unregister must be called when not needed and this
// will clean all memory allocated by the sim
static int gpi_free_recurring(p_vpi_cb_user_data user_data)
{
    FENTER
    int32_t rc;
    vpiHandle cb_hdl = user_data->cb_hdl;
    if (!cb_hdl) {
        LOG_ERROR("VPI: %s passed a NULL pointer\n", __func__);
        exit(1);
    }

    rc = vpi_remove_cb(cb_hdl);
    FEXIT
    return rc;
}

gpi_sim_hdl gpi_register_value_change_callback(int (*gpi_function)(void *), void *gpi_cb_data, gpi_sim_hdl gpi_hdl)
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
    user_data->cb_value.format = vpiIntVal;
    user_data->called = false;
    user_data->cleared = false;

    vpi_time_s.type = vpiSuppressTime;
    vpi_value_s.format = vpiIntVal;

    cb_data_s.reason    = cbValueChange;
    cb_data_s.cb_rtn    = handle_vpi_callback;
    cb_data_s.obj       = (vpiHandle)(gpi_hdl->sim_hdl);
    cb_data_s.time      = &vpi_time_s;
    cb_data_s.value     = &user_data->cb_value;
    cb_data_s.user_data = (char *)user_data;

    user_data->cb_hdl = vpi_register_cb(&cb_data_s);
    FEXIT

    return &user_data->gpi_hdl;
}


gpi_sim_hdl gpi_register_readonly_callback(int (*gpi_function)(void *), void *gpi_cb_data)
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
    user_data->called = false;
    user_data->cleared = false;

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
    return &user_data->gpi_hdl;
}

gpi_sim_hdl gpi_register_readwrite_callback(int (*gpi_function)(void *), void *gpi_cb_data)
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
    user_data->called = false;
    user_data->cleared = false;

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
    return &user_data->gpi_hdl;
}

gpi_sim_hdl gpi_register_nexttime_callback(int (*gpi_function)(void *), void *gpi_cb_data)
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
    user_data->called = false;
    user_data->cleared = false;

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
    return &user_data->gpi_hdl;
}

gpi_sim_hdl gpi_register_timed_callback(int (*gpi_function)(void *), void *gpi_cb_data, uint64_t time_ps)
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
    user_data->called = false;
    user_data->cleared = false;

    vpi_time_s.type = vpiSimTime;
    vpi_time_s.high = (uint32_t)(time_ps>>32);
    vpi_time_s.low  = (uint32_t)(time_ps);

    cb_data_s.reason    = cbAfterDelay;
    cb_data_s.cb_rtn    = handle_vpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = &vpi_time_s;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)user_data;

    user_data->cb_hdl = vpi_register_cb(&cb_data_s);
    FEXIT

    return &user_data->gpi_hdl;
}

gpi_sim_hdl gpi_register_sim_start_callback(int (*gpi_function)(void *), void *gpi_cb_data)
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
    user_data->called = false;
    user_data->cleared = false;

    cb_data_s.reason    = cbStartOfSimulation;
    cb_data_s.cb_rtn    = handle_vpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = NULL;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)user_data;

    user_data->cb_hdl = vpi_register_cb(&cb_data_s);
    FEXIT
    return &user_data->gpi_hdl;

}

gpi_sim_hdl gpi_register_sim_end_callback(int (*gpi_function)(void *), void *gpi_cb_data)
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
    user_data->called = false;
    user_data->cleared = false;

    cb_data_s.reason    = cbEndOfSimulation;
    cb_data_s.cb_rtn    = handle_vpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = NULL;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)user_data;

    user_data->cb_hdl = vpi_register_cb(&cb_data_s);
    FEXIT
    return &user_data->gpi_hdl;

}

int gpi_clock_handler(void *clock)
{
    gpi_clock_hdl hdl = (gpi_clock_hdl)clock;
    gpi_sim_hdl old_hdl;

    if (hdl->exit || (hdl->max_cycles == hdl->curr_cycle))
        return;

    /* Unregister/free the last callback that just fired */
    old_hdl = hdl->cb_hdl;

    hdl->value = !hdl->value;
    gpi_set_signal_value_int(hdl->clk_hdl, hdl->value);
    hdl->cb_hdl = gpi_register_timed_callback(gpi_clock_handler, hdl, hdl->period);
    hdl->curr_cycle++;

    gpi_deregister_callback(old_hdl);
}

gpi_sim_hdl gpi_clock_register(gpi_sim_hdl sim_hdl, int period, unsigned int cycles)
{
    FENTER

    gpi_clock_hdl hdl = malloc(sizeof(gpi_clock_t));
    if (!hdl)
        LOG_WARN("Unable to allocate memory");

    hdl->period = period;
    hdl->value = 0;
    hdl->clk_hdl = sim_hdl;
    hdl->exit = false;
    hdl->max_cycles = cycles;
    hdl->curr_cycle = 0;

    gpi_set_signal_value_int(hdl->clk_hdl, hdl->value);
    hdl->cb_hdl = gpi_register_timed_callback(gpi_clock_handler, hdl, hdl->period);

    FEXIT
    return &hdl->gpi_hdl;
}

void gpi_clock_unregister(gpi_sim_hdl clock)
{
    gpi_clock_hdl hdl = gpi_container_of(clock, gpi_clock_t, gpi_hdl);
    hdl->exit = true;
}

void register_embed(void)
{
    FENTER
    embed_init_python();
    FEXIT
}


int handle_sim_init(void *gpi_cb_data)
{
    FENTER
    s_vpi_vlog_info info_s;
    sim_init_cb = NULL;
    vpi_get_vlog_info(&info_s);
    embed_sim_init(&info_s);
    FEXIT
}

void register_initial_callback(void)
{
    FENTER
    sim_init_cb = gpi_register_sim_start_callback(handle_sim_init, (void *)NULL);
    FEXIT
}

int handle_sim_end(void *gpi_cb_data)
{
    FENTER
    if (sim_finish_cb)
        embed_sim_end();
    FEXIT
}

void register_final_callback(void)
{
    FENTER
    sim_finish_cb = gpi_register_sim_end_callback(handle_sim_end, (void *)NULL);
    FEXIT
}

// If the Pything world wants things to shut down then unregister
// the callback for end of sim
void gpi_sim_end()
{
    FENTER

    sim_finish_cb = NULL;
    vpi_control(vpiFinish);

    FEXIT
}

void (*vlog_startup_routines[])() = {
    register_embed,
    register_initial_callback,
    register_final_callback,
    0
};


// For non-VPI compliant applications that cannot find vlog_startup_routines symbol
void vlog_startup_routines_bootstrap() {
    void (*routine)(void);
    int i;
    routine = vlog_startup_routines[0];
    for (i = 0, routine = vlog_startup_routines[i];
         routine;
         routine = vlog_startup_routines[++i]) {
        routine();
    }
}
