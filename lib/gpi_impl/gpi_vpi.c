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
#include <vpi_user.h>

#define VPI_CHECKING 1

static gpi_sim_hdl sim_init_cb;
static gpi_sim_hdl sim_finish_cb;

typedef enum vpi_cb_state_e {
    VPI_FREE = 0,
    VPI_PRIMED = 1,
    VPI_PRE_CALL = 2,
    VPI_POST_CALL = 3,
    VPI_DELETE = 4,
} vpi_cb_state_t;

// callback user data used for VPI callbacks

typedef struct t_vpi_cb {
    vpiHandle cb_hdl;
    s_vpi_value  cb_value;
    vpi_cb_state_t state;
    gpi_cb_hdl_t gpi_cb_data;
    int (*vpi_cleanup)(struct t_vpi_cb *cb_data);
} s_vpi_cb, *p_vpi_cb;

// Forward declarations
static int vpi_deregister_callback(gpi_sim_hdl gpi_hdl);
static void vpi_destroy_cb_handle(gpi_cb_hdl hdl);

// Add to this over time
static const char * vpi_reason_to_string(int reason)
{
    switch (reason) {
    case cbValueChange:
        return "cbValueChange";
    case cbAtStartOfSimTime:
        return "cbAtStartOfSimTime";
    case cbReadWriteSynch:
        return "cbReadWriteSynch";
    case cbReadOnlySynch:
        return "cbReadOnlySynch";
    case cbNextSimTime:
        return "cbNextSimTime";
    case cbAfterDelay:
        return "cbAfterDelay";
    case cbStartOfSimulation:
        return "cbStartOfSimulation";
    case cbEndOfSimulation:
        return "cbEndOfSimulation";
    default:
        return "unknown";
    }
}


// Should be run after every VPI call to check error status
static int __check_vpi_error(const char *func, long line)
{
    int level=0;
#if VPI_CHECKING
    s_vpi_error_info info;
    int loglevel;
    level = vpi_chk_error(&info);
    if (level == 0)
        return 0;

    switch (level) {
        case vpiNotice:
            loglevel = GPIInfo;
            break;
        case vpiWarning:
            loglevel = GPIWarning;
            break;
        case vpiError:
            loglevel = GPIError;
            break;
        case vpiSystem:
        case vpiInternal:
            loglevel = GPICritical;
            break;
    }

    gpi_log("cocotb.gpi", loglevel, __FILE__, func, line,
            "VPI Error level %d\nPROD %s\nCODE %s\nFILE %s",
            info.message, info.product, info.code, info.file);

#endif
    return level;
}

#define check_vpi_error() \
    __check_vpi_error(__func__, __LINE__)

static inline int __vpi_register_cb(p_vpi_cb user, p_cb_data cb_data)
{
    /* If the user data already has a callback handle then deregister
     * before getting the new one
     */
    if (user->state == VPI_PRIMED) {
        fprintf(stderr, "Attempt to prime an already primed trigger for %s!\n", 
                                        vpi_reason_to_string(cb_data->reason));
    }

    vpiHandle new_hdl = vpi_register_cb(cb_data);
    int ret = 0;

    if (!new_hdl) {
        LOG_CRITICAL("VPI: Unable to register callback a handle for VPI type %s(%d)",
                     vpi_reason_to_string(cb_data->reason), cb_data->reason);
        check_vpi_error();
        ret = -1;
    }

    if (user->cb_hdl != NULL) {
        fprintf(stderr, "user->gpi_cb_hdl is not null, deregistering %s!\n",
                                        vpi_reason_to_string(cb_data->reason));
        vpi_deregister_callback(&user->gpi_cb_data.hdl);
    }

    user->cb_hdl = new_hdl;
    user->state = VPI_PRIMED;

    return ret;
}


// Handle related functions
/**
 * @name    Find the root handle
 * @brief   Find the root handle using a optional name
 *
 * Get a handle to the root simulator object.  This is usually the toplevel.
 *
 * If no name is defined, we return the first root instance.
 *
 * If name is provided, we check the name against the available objects until
 * we find a match.  If no match is found we return NULL
 */
static gpi_sim_hdl vpi_get_root_handle(const char* name)
{
    FENTER
    vpiHandle root;
    vpiHandle iterator;
    gpi_sim_hdl rv;

    // vpi_iterate with a ref of NULL returns the top level module
    iterator = vpi_iterate(vpiModule, NULL);
    check_vpi_error();

    for (root = vpi_scan(iterator); root != NULL; root = vpi_scan(iterator)) {

        if (name == NULL || !strcmp(name, vpi_get_str(vpiFullName, root)))
            break;
    }

    if (!root) {
        check_vpi_error();
        goto error;
    }

    // Need to free the iterator if it didn't return NULL
    if (!vpi_free_object(iterator)) {
        LOG_WARN("VPI: Attempting to free root iterator failed!");
        check_vpi_error();
    }

    rv = gpi_create_handle();
    rv->sim_hdl = root;

    FEXIT
    return rv;

  error:

    LOG_CRITICAL("VPI: Couldn't find root handle %s", name);

    iterator = vpi_iterate(vpiModule, NULL);

    for (root = vpi_scan(iterator); root != NULL; root = vpi_scan(iterator)) {

        LOG_CRITICAL("VPI: Toplevel instances: %s != %s...", name, vpi_get_str(vpiFullName, root));

        if (name == NULL || !strcmp(name, vpi_get_str(vpiFullName, root)))
            break;
    }

    FEXIT
    return NULL;
}


/**
 * @brief   Get a handle to an object under the scope of parent
 *
 * @param   name of the object to find
 * @param   parent handle to parent object defining the scope to search
 *
 * @return  gpi_sim_hdl for the new object or NULL if object not found
 */
static gpi_sim_hdl vpi_get_handle_by_name(const char *name, gpi_sim_hdl parent)
{
    FENTER
    gpi_sim_hdl rv;
    vpiHandle obj;
    vpiHandle iterator;
    int len;
    char *buff;

    // Structures aren't technically a scope, according to the LRM. If parent
    // is a structure then we have to iterate over the members comparing names
    if (vpiStructVar == vpi_get(vpiType, (vpiHandle)(parent->sim_hdl))) {

        iterator = vpi_iterate(vpiMember, (vpiHandle)(parent->sim_hdl));

        for (obj = vpi_scan(iterator); obj != NULL; obj = vpi_scan(iterator)) {

            if (!strcmp(name, strrchr(vpi_get_str(vpiName, obj), 46) + 1))
                break;
        }

        if (!obj)
            return NULL;

        // Need to free the iterator if it didn't return NULL
        if (!vpi_free_object(iterator)) {
            LOG_WARN("VPI: Attempting to free root iterator failed!");
            check_vpi_error();
        }

        goto success;
    }

    if (name)
        len = strlen(name) + 1;

    buff = (char *)malloc(len);
    if (buff == NULL) {
        LOG_CRITICAL("VPI: Attempting allocate string buffer failed!");
        return NULL;
    }

    strncpy(buff, name, len);
    obj = vpi_handle_by_name(buff, (vpiHandle)(parent->sim_hdl));
    if (!obj) {
        LOG_DEBUG("VPI: Handle '%s' not found!", name);

        // NB we deliberately don't dump an error message here because it's
        // a valid use case to attempt to grab a signal by name - for example
        // optional signals on a bus.
        // check_vpi_error();
        free(buff);
        return NULL;
    }

    free(buff);

success:
    rv = gpi_create_handle();
    rv->sim_hdl = obj;

    FEXIT
    return rv;
}

/**
 * @brief   Get a handle for an object based on its index within a parent
 *
 * @param parent <gpi_sim_hdl> handle to the parent
 * @param indext <uint32_t> Index to retrieve
 *
 * Can be used on bit-vectors to access a specific bit or
 * memories to access an address
 */
static gpi_sim_hdl vpi_get_handle_by_index(gpi_sim_hdl parent, uint32_t index)
{
    FENTER
    gpi_sim_hdl rv;
    vpiHandle obj;

    obj = vpi_handle_by_index((vpiHandle)(parent->sim_hdl), index);
    if (!obj) {
        LOG_ERROR("VPI: Handle idx '%d' not found!", index);
        return NULL;
    }

    rv = gpi_create_handle();
    rv->sim_hdl = obj;

    FEXIT
    return rv;
}


// Functions for iterating over entries of a handle
// Returns an iterator handle which can then be used in gpi_next calls
// NB May return NULL if no objects of the request type exist
static gpi_iterator_hdl vpi_iterate_hdl(uint32_t type, gpi_sim_hdl base) {
    FENTER

    vpiHandle iterator;

    iterator = vpi_iterate(type, (vpiHandle)(base->sim_hdl));
    check_vpi_error();

    FEXIT
    return (gpi_iterator_hdl)iterator;
}

// Returns NULL when there are no more objects
static gpi_sim_hdl vpi_next_hdl(gpi_iterator_hdl iterator)
{
    FENTER
    gpi_sim_hdl rv = gpi_create_handle();

    rv->sim_hdl = vpi_scan((vpiHandle) iterator);
    check_vpi_error();
    if (!rv->sim_hdl) {
        gpi_free_handle(rv);
        rv = NULL;
    }

    // Don't need to call vpi_free_object on the iterator handle
    // From VPI spec:
    // After returning NULL, memory associated with the iteratod handle is
    // freed, making the handle invalid.

    FEXIT
    return rv;
}

// double gpi_get_sim_time()
static void vpi_get_sim_time(uint32_t *high, uint32_t *low)
{
    s_vpi_time vpi_time_s;
    vpi_time_s.type = vpiSimTime;//vpiScaledRealTime;        //vpiSimTime;
    vpi_get_time(NULL, &vpi_time_s);
    check_vpi_error();
    *high = vpi_time_s.high;
    *low = vpi_time_s.low;
}

// Value related functions
static void vpi_set_signal_value_int(gpi_sim_hdl gpi_hdl, int value)
{
    FENTER
    s_vpi_value value_s;
    p_vpi_value value_p = &value_s;

    value_p->value.integer = value;
    value_p->format = vpiIntVal;

    s_vpi_time vpi_time_s;
    p_vpi_time vpi_time_p = &vpi_time_s;

    vpi_time_p->type = vpiSimTime;
    vpi_time_p->high = 0;
    vpi_time_p->low  = 0;

    // Use Inertial delay to schedule an event, thus behaving like a verilog testbench
    vpi_put_value((vpiHandle)(gpi_hdl->sim_hdl), value_p, vpi_time_p, vpiInertialDelay);
    check_vpi_error();

    FEXIT
}

static void vpi_set_signal_value_str(gpi_sim_hdl gpi_hdl, const char *str)
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
    check_vpi_error();
    free(buff);
    FEXIT
}

static char *vpi_get_signal_value_binstr(gpi_sim_hdl gpi_hdl)
{
    FENTER
    s_vpi_value value_s = {vpiBinStrVal};
    p_vpi_value value_p = &value_s;

    vpi_get_value((vpiHandle)(gpi_hdl->sim_hdl), value_p);
    check_vpi_error();

    char *result = gpi_copy_name(value_p->value.str);
    FEXIT
    return result;
}

static char *vpi_get_signal_name_str(gpi_sim_hdl gpi_hdl)
{
    FENTER
    const char *name = vpi_get_str(vpiFullName, (vpiHandle)(gpi_hdl->sim_hdl));
    check_vpi_error();
    char *result = gpi_copy_name(name);
    FEXIT
    return result;
}

static char *vpi_get_signal_type_str(gpi_sim_hdl gpi_hdl)
{
    FENTER
    const char *name = vpi_get_str(vpiType, (vpiHandle)(gpi_hdl->sim_hdl));
    check_vpi_error();
    char *result = gpi_copy_name(name);
    FEXIT
    return result;
}


// Callback related functions
static int32_t handle_vpi_callback(p_cb_data cb_data)
{
    FENTER
    int rv = 0;
    //vpiHandle old_cb;

    p_vpi_cb user_data;
    user_data = (p_vpi_cb)cb_data->user_data;

    if (!user_data)
        LOG_CRITICAL("VPI: Callback data corrupted");

    user_data->state = VPI_PRE_CALL;
    //old_cb = user_data->cb_hdl;
    gpi_handle_callback(&user_data->gpi_cb_data.hdl);
    
// HACK: Investigate further - this breaks modelsim
#if 0
    if (old_cb == user_data->cb_hdl)
        gpi_deregister_callback(&user_data->gpi_hdl);
#endif

    /* A request to delete could have been done
     * inside gpi_function
     */
    if (user_data->state == VPI_DELETE)
        gpi_free_cb_handle(&user_data->gpi_cb_data.hdl);
    else
        user_data->state = VPI_POST_CALL;

    FEXIT
    return rv;
};


/* Deregister a prior set up callback with the simulator
 * The handle must have been allocated with gpi_create_cb_handle
 * This can be called at any point between
 * gpi_create_cb_handle and gpi_free_cb_handle
 */
static int vpi_deregister_callback(gpi_sim_hdl gpi_hdl)
{   
    FENTER
    p_vpi_cb vpi_user_data;
    gpi_cb_hdl gpi_user_data;
    int rc = 1;
    // We should be able to user vpi_get_cb_info
    // but this is not implemented in ICARUS
    // and gets upset on VCS. So instead we
    // do some pointer magic.
   
    gpi_user_data = gpi_container_of(gpi_hdl, gpi_cb_hdl_t, hdl);
    vpi_user_data = gpi_container_of(gpi_user_data, s_vpi_cb, gpi_cb_data);

    if (vpi_user_data->cb_hdl) {
        rc = vpi_user_data->vpi_cleanup(vpi_user_data);
        vpi_user_data->cb_hdl = NULL;
    }

    FEXIT
    GPI_RET(rc);
}


// Call when the handle relates to a one time callback
// No need to call vpi_deregister_cb as the sim will
// do this but do need to destroy the handle
static int vpi_free_one_time(p_vpi_cb user_data)
{
    FENTER
    int rc;
    vpiHandle cb_hdl = user_data->cb_hdl;
    if (!cb_hdl) {
        LOG_CRITICAL("VPI: passed a NULL pointer : ABORTING");
        exit(1);
    }

    // If the callback has not been called we also need to call
    // remove as well
    if (user_data->state == VPI_PRIMED) {

        rc = vpi_remove_cb(cb_hdl);
        if (!rc) {
            check_vpi_error();
            return rc;
        }
        user_data->cb_hdl = NULL;

// HACK: Calling vpi_free_object after vpi_remove_cb causes Modelsim to VPIEndOfSimulationCallback
#if 0
        rc = vpi_free_object(cb_hdl);
        if (!rc) {
            check_vpi_error();
            return rc;
        }
#endif
    }
    user_data->state = VPI_FREE;
    FEXIT
    return rc;
}


// Call when the handle relates to recurring callback
// Unregister must be called when not needed and this
// will clean all memory allocated by the sim
static int vpi_free_recurring(p_vpi_cb user_data)
{
    FENTER
    int rc;
    vpiHandle cb_hdl = user_data->cb_hdl;
    if (!cb_hdl) {
        LOG_CRITICAL("VPI: passed a NULL pointer : ABORTING");
        exit(1);
    }

    rc = vpi_remove_cb(cb_hdl);
    check_vpi_error();
    FEXIT
    return rc;
}

/* These functions request a callback to be active with the current
 * handle and associated data. A callback handle needs to have been
 * allocated with gpi_create_cb_handle first
 */


static int vpi_register_value_change_callback(gpi_sim_hdl cb,
                                              int (*gpi_function)(void *),
                                              void *gpi_cb_data,
                                              gpi_sim_hdl gpi_hdl)
{
    FENTER
 
    int ret;
    s_cb_data cb_data_s;
    s_vpi_time vpi_time_s;
    p_vpi_cb vpi_user_data;
    gpi_cb_hdl gpi_user_data;

    gpi_user_data = gpi_container_of(cb, gpi_cb_hdl_t, hdl);
    vpi_user_data = gpi_container_of(gpi_user_data, s_vpi_cb, gpi_cb_data);

    vpi_user_data->vpi_cleanup = vpi_free_recurring;
    vpi_user_data->cb_value.format = vpiIntVal;

    vpi_time_s.type = vpiSuppressTime;

    cb_data_s.reason    = cbValueChange;
    cb_data_s.cb_rtn    = handle_vpi_callback;
    cb_data_s.obj       = (vpiHandle)(gpi_hdl->sim_hdl);
    cb_data_s.time      = &vpi_time_s;
    cb_data_s.value     = &vpi_user_data->cb_value;
    cb_data_s.user_data = (char *)vpi_user_data;

    ret = __vpi_register_cb(vpi_user_data, &cb_data_s);

    FEXIT

    return ret;
}

static int vpi_register_readonly_callback(gpi_sim_hdl cb,
                                          int (*gpi_function)(void *),
                                          void *gpi_cb_data)
{
    FENTER

    int ret;
    s_cb_data cb_data_s;
    s_vpi_time vpi_time_s;
    p_vpi_cb vpi_user_data;
    gpi_cb_hdl gpi_user_data;

    gpi_user_data = gpi_container_of(cb, gpi_cb_hdl_t, hdl);
    vpi_user_data = gpi_container_of(gpi_user_data, s_vpi_cb, gpi_cb_data);

    vpi_user_data->vpi_cleanup = vpi_free_one_time;

    vpi_time_s.type = vpiSimTime;
    vpi_time_s.high = 0;
    vpi_time_s.low = 0;

    cb_data_s.reason    = cbReadOnlySynch;
    cb_data_s.cb_rtn    = handle_vpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = &vpi_time_s;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)vpi_user_data;

    ret = __vpi_register_cb(vpi_user_data, &cb_data_s);

    FEXIT
    return ret;
}

static int vpi_register_readwrite_callback(gpi_sim_hdl cb,
                                           int (*gpi_function)(void *),
                                           void *gpi_cb_data)
{
    FENTER

    int ret;
    s_cb_data cb_data_s;
    s_vpi_time vpi_time_s;
    p_vpi_cb vpi_user_data;
    gpi_cb_hdl gpi_user_data;

    gpi_user_data = gpi_container_of(cb, gpi_cb_hdl_t, hdl);
    vpi_user_data = gpi_container_of(gpi_user_data, s_vpi_cb, gpi_cb_data);

    vpi_user_data->vpi_cleanup = vpi_free_one_time;

    vpi_time_s.type = vpiSimTime;
    vpi_time_s.high = 0;
    vpi_time_s.low = 0;

    cb_data_s.reason    = cbReadWriteSynch;
    cb_data_s.cb_rtn    = handle_vpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = &vpi_time_s;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)vpi_user_data;

    ret = __vpi_register_cb(vpi_user_data, &cb_data_s);

    FEXIT
    return ret;
}


static int vpi_register_nexttime_callback(gpi_sim_hdl cb,
                                          int (*gpi_function)(void *),
                                          void *gpi_cb_data)
{
    FENTER
    
    int ret;
    s_cb_data cb_data_s;
    s_vpi_time vpi_time_s;
    p_vpi_cb vpi_user_data;
    gpi_cb_hdl gpi_user_data;

    gpi_user_data = gpi_container_of(cb, gpi_cb_hdl_t, hdl);
    vpi_user_data = gpi_container_of(gpi_user_data, s_vpi_cb, gpi_cb_data);

    vpi_user_data->vpi_cleanup = vpi_free_one_time;

    vpi_time_s.type = vpiSimTime;
    vpi_time_s.high = 0;
    vpi_time_s.low = 0;

    cb_data_s.reason    = cbNextSimTime;
    cb_data_s.cb_rtn    = handle_vpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = &vpi_time_s;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)vpi_user_data;

    ret = __vpi_register_cb(vpi_user_data, &cb_data_s);
  
    FEXIT
    return ret;
}
 
static int vpi_register_timed_callback(gpi_sim_hdl cb,
                                       int (*gpi_function)(void *),
                                       void *gpi_cb_data,
                                       uint64_t time_ps)
{
    FENTER

    int ret;
    s_cb_data cb_data_s;
    s_vpi_time vpi_time_s;
    p_vpi_cb vpi_user_data;
    gpi_cb_hdl gpi_user_data;

    gpi_user_data = gpi_container_of(cb, gpi_cb_hdl_t, hdl);
    vpi_user_data = gpi_container_of(gpi_user_data, s_vpi_cb, gpi_cb_data);

    vpi_user_data->vpi_cleanup = vpi_free_one_time;

    vpi_time_s.type = vpiSimTime;
    vpi_time_s.high = (uint32_t)(time_ps>>32);
    vpi_time_s.low  = (uint32_t)(time_ps);

    cb_data_s.reason    = cbAfterDelay;
    cb_data_s.cb_rtn    = handle_vpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = &vpi_time_s;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)vpi_user_data;

    ret = __vpi_register_cb(vpi_user_data, &cb_data_s);

    FEXIT

    return ret;
}


/* Checking of validity is done in the common code */
static gpi_cb_hdl vpi_create_cb_handle(void)
{
    gpi_cb_hdl ret = NULL;

    FENTER

    p_vpi_cb new_cb_hdl = calloc(1, sizeof(*new_cb_hdl));
    if (new_cb_hdl)
        ret = &new_cb_hdl->gpi_cb_data;

    FEXIT
    return ret;
}

static void vpi_destroy_cb_handle(gpi_cb_hdl hdl)
{
    FENTER
    p_vpi_cb vpi_hdl = gpi_container_of(hdl, s_vpi_cb, gpi_cb_data);
    free(vpi_hdl);
    FEXIT
}

static void *vpi_get_callback_data(gpi_sim_hdl gpi_hdl)
{
    FENTER
    gpi_cb_hdl gpi_user_data;
    gpi_user_data = gpi_container_of(gpi_hdl, gpi_cb_hdl_t, hdl);
    return gpi_user_data->gpi_cb_data;
}


// If the Pything world wants things to shut down then unregister
// the callback for end of sim
static void vpi_sim_end(void)
{
    sim_finish_cb = NULL;
    vpi_control(vpiFinish);
    check_vpi_error();
}

static s_gpi_impl_tbl vpi_table = {
    .sim_end = vpi_sim_end,
    .iterate_handle = vpi_iterate_hdl,
    .next_handle = vpi_next_hdl,
    .create_cb_handle = vpi_create_cb_handle,
    .destroy_cb_handle = vpi_destroy_cb_handle,
    .deregister_callback = vpi_deregister_callback,
    .get_root_handle = vpi_get_root_handle,
    .get_sim_time = vpi_get_sim_time,
    .get_handle_by_name = vpi_get_handle_by_name,
    .get_handle_by_index = vpi_get_handle_by_index,
    .get_signal_name_str = vpi_get_signal_name_str,
    .get_signal_type_str = vpi_get_signal_type_str,
    .get_signal_value_binstr = vpi_get_signal_value_binstr,
    .set_signal_value_int = vpi_set_signal_value_int,
    .set_signal_value_str = vpi_set_signal_value_str,
    .register_timed_callback = vpi_register_timed_callback,
    .register_readwrite_callback = vpi_register_readwrite_callback,
    .register_nexttime_callback = vpi_register_nexttime_callback,
    .register_value_change_callback = vpi_register_value_change_callback,
    .register_readonly_callback = vpi_register_readonly_callback,
    .get_callback_data = vpi_get_callback_data,
};

static void register_embed(void)
{
    gpi_register_impl(&vpi_table, 0xfeed);
    gpi_embed_init_python();
}


static int handle_sim_init(void *gpi_cb_data)
{
    FENTER
    s_vpi_vlog_info info;
    gpi_sim_info_t sim_info;

    vpi_get_vlog_info(&info);

    sim_info.argc = info.argc;
    sim_info.argv = info.argv;
    sim_info.product = info.product;
    sim_info.version = info.version;

    gpi_embed_init(&sim_info);

    FEXIT

    return 0;
}

static void register_initial_callback(void)
{
    FENTER

    s_cb_data cb_data_s;
    p_vpi_cb vpi_user_data;
    gpi_cb_hdl gpi_user_data;

    sim_init_cb = gpi_create_cb_handle();

    gpi_user_data = gpi_container_of(sim_init_cb, gpi_cb_hdl_t, hdl);
    vpi_user_data = gpi_container_of(gpi_user_data, s_vpi_cb, gpi_cb_data);

    gpi_user_data->gpi_cb_data = NULL;
    gpi_user_data->gpi_function = handle_sim_init;
    
    vpi_user_data->vpi_cleanup = vpi_free_one_time;

    cb_data_s.reason    = cbStartOfSimulation;
    cb_data_s.cb_rtn    = handle_vpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = NULL;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)vpi_user_data;

    /* We ignore the return value here as VCS does some silly
     * things on comilation that means it tries to run through
     * the vlog_startup_routines and so call this routine
     */
    __vpi_register_cb(vpi_user_data, &cb_data_s);

    FEXIT
}

static int handle_sim_end(void *gpi_cb_data)
{
    FENTER
    if (sim_finish_cb) {
        sim_finish_cb = NULL;
        /* This means that we have been asked to close */
        gpi_embed_end();
    } /* Other sise we have already been here from the top down so do not need
         to inform the upper layers that anything has occoured */
    gpi_free_cb_handle(sim_init_cb);
    FEXIT

    return 0;
}

static void register_final_callback(void)
{
    FENTER

    s_cb_data cb_data_s;
    p_vpi_cb vpi_user_data;
    gpi_cb_hdl gpi_user_data;

    sim_init_cb = gpi_create_cb_handle();

    gpi_user_data = gpi_container_of(sim_init_cb, gpi_cb_hdl_t, hdl);
    vpi_user_data = gpi_container_of(gpi_user_data, s_vpi_cb, gpi_cb_data);

    gpi_user_data->gpi_cb_data = NULL;
    gpi_user_data->gpi_function = handle_sim_end;

    vpi_user_data->vpi_cleanup = vpi_free_one_time;

    cb_data_s.reason    = cbEndOfSimulation;
    cb_data_s.cb_rtn    = handle_vpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = NULL;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)vpi_user_data;

    /* We ignore the return value here as VCS does some silly
     * things on comilation that means it tries to run through
     * the vlog_startup_routines and so call this routine
     */
    __vpi_register_cb(vpi_user_data, &cb_data_s);
 
    FEXIT
}


// Called at compile time to validate the arguments to the system functions
// we redefine (info, warning, error, fatal).
//
// Expect either no arguments or a single string
static int system_function_compiletf(char *userdata)
{
    vpiHandle systf_handle, arg_iterator, arg_handle;
    int tfarg_type;

    systf_handle = vpi_handle(vpiSysTfCall, NULL);
    arg_iterator = vpi_iterate(vpiArgument, systf_handle);

    if (arg_iterator == NULL)
        return 0;

    arg_handle = vpi_scan(arg_iterator);
    tfarg_type = vpi_get(vpiType, arg_handle);

    // FIXME: HACK for some reason Icarus returns a vpiRealVal type for strings?
    if (vpiStringVal != tfarg_type && vpiRealVal != tfarg_type) {
        vpi_printf("ERROR: $[info|warning|error|fata] argument wrong type: %d\n",
                    tfarg_type);
        vpi_free_object(arg_iterator);
        vpi_control(vpiFinish, 1);
        return -1;
    }
    return 0;
}

static int systf_info_level           = GPIInfo;
static int systf_warning_level        = GPIWarning;
static int systf_error_level          = GPIError;
static int systf_fatal_level          = GPICritical;

// System function to permit code in the simulator to fail a test
// TODO: Pass in an error string
static int system_function_overload(char *userdata)
{
    vpiHandle systfref, args_iter, argh;
    struct t_vpi_value argval;
    const char *msg = "*** NO MESSAGE PROVIDED ***";

    // Obtain a handle to the argument list
    systfref = vpi_handle(vpiSysTfCall, NULL);
    args_iter = vpi_iterate(vpiArgument, systfref);

    // The first argument to fatal is the FinishNum which we discard
    if (args_iter && *userdata == systf_fatal_level) {
        argh = vpi_scan(args_iter);
    }

    if (args_iter) {
        // Grab the value of the first argument
        argh = vpi_scan(args_iter);
        argval.format = vpiStringVal;
        vpi_get_value(argh, &argval);
        vpi_free_object(args_iter);
        msg = argval.value.str;
    }

    gpi_log("simulator", *userdata, vpi_get_str(vpiFile, systfref), "", (long)vpi_get(vpiLineNo, systfref), msg );

    // Fail the test for critical errors
    if (GPICritical == *userdata)
        embed_sim_event(SIM_TEST_FAIL, argval.value.str);

    return 0;
}

static void register_system_functions(void)
{
    FENTER
    s_vpi_systf_data tfData = { vpiSysTask, vpiSysTask };

    tfData.sizetf       = NULL;
    tfData.compiletf    = system_function_compiletf;
    tfData.calltf       = system_function_overload;

    tfData.user_data    = (void *)&systf_info_level;
    tfData.tfname       = "$info";
    vpi_register_systf( &tfData );

    tfData.user_data    = (void *)&systf_warning_level;
    tfData.tfname       = "$warning";
    vpi_register_systf( &tfData );

    tfData.user_data    = (void *)&systf_error_level;
    tfData.tfname       = "$error";
    vpi_register_systf( &tfData );

    tfData.user_data    = (void *)&systf_fatal_level;
    tfData.tfname       = "$fatal";
    vpi_register_systf( &tfData );

    FEXIT
}

void (*vlog_startup_routines[])(void) = {
    register_embed,
    register_system_functions,
    register_initial_callback,
    register_final_callback,
    0
};


// For non-VPI compliant applications that cannot find vlog_startup_routines symbol
void vlog_startup_routines_bootstrap(void) {
    void (*routine)(void);
    int i;
    routine = vlog_startup_routines[0];
    for (i = 0, routine = vlog_startup_routines[i];
         routine;
         routine = vlog_startup_routines[++i]) {
        routine();
    }
}
