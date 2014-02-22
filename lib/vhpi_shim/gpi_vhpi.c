/******************************************************************************
* Copyright (c) 2014 Potential Ventures Ltd
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


#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>

#include <gpi.h>
#include <gpi_logging.h>
#include <embed.h>
#include <vhpi_user.h>

#define gpi_container_of(_address, _type, _member)  \
        ((_type *)((uintptr_t)(_address) -      \
         (uintptr_t)(&((_type *)0)->_member)))

#define VPI_CHECKING 1

static gpi_sim_hdl sim_init_cb;
static gpi_sim_hdl sim_finish_cb;

static int alloc_count = 0;
static int dealloc_count = 0;
static int clear_count = 0;
static int total_count = 0;

typedef enum vhpi_cb_state_e {
    VHPI_FREE = 0,
    VHPI_PRIMED = 1,
    VHPI_PRE_CALL = 2,
    VHPI_POST_CALL = 3,
    VHPI_DELETE = 4,
} vhpi_cb_state_t;

// callback user data used for VPI callbacks
// (mostly just a thin wrapper around the gpi_callback)
typedef struct t_vhpi_cb_user_data {
    void *gpi_cb_data;
    int (*gpi_function)(void *);
    int (*gpi_cleanup)(struct t_vhpi_cb_user_data *);
    vhpiHandleT         cb_hdl;
    vhpiValueT          cb_value;
    gpi_sim_hdl_t       gpi_hdl;
    vhpi_cb_state_t      state;
} s_vhpi_cb_user_data, *p_vhpi_cb_user_data;

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

// Add to this over time
static const char * vhpi_reason_to_string(int reason)
{
    switch (reason) {
    case vhpiCbValueChange:
        return "vhpiCbValueChange";
    case vhpiCbStartOfNextCycle:
        return "vhpiCbStartOfNextCycle";
    case vhpiCbStartOfPostponed:
        return "vhpiCbStartOfPostponed";
    case vhpiCbEndOfTimeStep:
        return "vhpiCbEndOfTimeStep";
    case vhpiCbNextTimeStep:
        return "vhpiCbNextTimeStep";
    case vhpiCbAfterDelay:
        return "vhpiCbAfterDelay";
    case vhpiCbStartOfSimulation:
        return "vhpiCbStartOfSimulation";
    case vhpiCbEndOfSimulation:
        return "vhpiCbEndOfSimulation";
    default:
        return "unknown";
    }
}

// Should be run after every VPI call to check error status
static int __check_vhpi_error(const char *func, long line)
{
    int level=0;
#if VPI_CHECKING
    vhpiErrorInfoT info;
    int loglevel;
    level = vhpi_check_error(&info);
    if (level == 0)
        return;

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
            "VPI Error level %d: %s\nFILE %s:%d",
            info.severity, info.message, info.file, info.line);

#endif
    return level;
}

#define check_vhpi_error() \
    __check_vhpi_error(__func__, __LINE__)

static inline int __gpi_register_cb(p_vhpi_cb_user_data user, vhpiCbDataT *cb_data)
{
    /* If the user data already has a callback handle then deregister
     * before getting the new one
     */
    vhpiHandleT new_hdl = vhpi_register_cb(cb_data, vhpiReturnCb);
    int ret = 0;

    if (!new_hdl) {
        LOG_CRITICAL("VPI: Unable to register callback a handle for VHPI type %s(%d)",
                     vhpi_reason_to_string(cb_data->reason), cb_data->reason);
        check_vhpi_error();
        ret = -1;
    }

    if (user->cb_hdl != NULL)
        gpi_deregister_callback(&user->gpi_hdl);

    user->cb_hdl = new_hdl;

    return ret;
}

static inline p_vhpi_cb_user_data __gpi_alloc_user(void)
{
    p_vhpi_cb_user_data new_data = calloc(1, sizeof(*new_data));
    if (new_data == NULL) {
        LOG_CRITICAL("VPI: Attempting allocate user_data failed!");
    }

    return new_data;
}

static inline void __gpi_free_callback(gpi_sim_hdl gpi_hdl)
{
    FENTER
    p_vhpi_cb_user_data user_data;
    user_data = gpi_container_of(gpi_hdl, s_vhpi_cb_user_data, gpi_hdl);

    free(user_data);
    FEXIT
}

void gpi_free_handle(gpi_sim_hdl gpi_hdl)
{
    free(gpi_hdl);
}

static gpi_sim_hdl gpi_alloc_handle(void)
{
    gpi_sim_hdl new_hdl = calloc(1, sizeof(*new_hdl));
    if (!new_hdl) {
        LOG_CRITICAL("VPI: Could not allocate handle");
        exit(1);
    }

    return new_hdl;
}

// Handle related functions
/**
 * @name    Find the root handle
 * @brief   Find the root handle using a optional name
 *
 * Get a handle to the root simulator object.  This is usually the toplevel.
 *
 * FIXME: In VHPI we always return the first root instance
 * 
 * TODO: Investigate possibility of iterating and checking names as per VHPI
 * If no name is defined, we return the first root instance.
 *
 * If name is provided, we check the name against the available objects until
 * we find a match.  If no match is found we return NULL
 */
gpi_sim_hdl gpi_get_root_handle(const char* name)
{
    FENTER
    vhpiHandleT root;
    gpi_sim_hdl rv;

    root = vhpi_handle(vhpiRootInst, NULL);
    check_vhpi_error();

    if (!root) {
        LOG_ERROR("VHPI: Attempting to get the root handle failed");
        FEXIT
        return NULL;
    }

    const char *found = vhpi_get_str(vhpiFullNameP, root);
    check_vhpi_error();

    if (name != NULL && strcmp(name, found)) {
        LOG_WARN("VHPI: Root %s doesn't match requested toplevel %s", name, found);
        FEXIT
        return NULL;
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
    vhpiHandleT obj;
    int len;
    char *buff;
    if (name)
        len = strlen(name) + 1;

    buff = (char *)malloc(len);
    if (buff == NULL) {
        LOG_CRITICAL("VHPI: Attempting allocate string buffer failed!");
        return NULL;
    }

    strncpy(buff, name, len);
    obj = vhpi_handle_by_name(buff, (vhpiHandleT)(parent->sim_hdl));
    if (!obj) {
        LOG_DEBUG("VHPI: Handle '%s' not found!", name);
//         check_vhpi_error();
        return NULL;
    }

    free(buff);

    rv = gpi_alloc_handle();
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
gpi_sim_hdl gpi_get_handle_by_index(gpi_sim_hdl parent, uint32_t index)
{
    FENTER
    gpi_sim_hdl rv;
    vhpiHandleT obj;

    obj = vhpi_handle_by_index(vhpiParamDecls, (vhpiHandleT)(parent->sim_hdl), index);
    if (!obj) {
        LOG_ERROR("VHPI: Handle idx '%d' not found!", index);
        return NULL;
    }

    rv = gpi_alloc_handle();
    rv->sim_hdl = obj;

    FEXIT
    return rv;
}


// Functions for iterating over entries of a handle
// Returns an iterator handle which can then be used in gpi_next calls
// NB May return NULL if no objects of the request type exist
gpi_iterator_hdl gpi_iterate(uint32_t type, gpi_sim_hdl base) {
    FENTER

    vhpiHandleT iterator;

    iterator = vhpi_iterator(type, (vhpiHandleT)(base->sim_hdl));
    check_vhpi_error();

    FEXIT
    return (gpi_iterator_hdl)iterator;
}

// Returns NULL when there are no more objects
gpi_sim_hdl gpi_next(gpi_iterator_hdl iterator)
{
    FENTER
    vhpiHandleT result;
    gpi_sim_hdl rv = gpi_alloc_handle();

    rv->sim_hdl = vhpi_scan((vhpiHandleT) iterator);
    check_vhpi_error();
    if (!rv->sim_hdl) {
        gpi_free_handle(rv);
        rv = NULL;
    }
    FEXIT
    return rv;
}

void gpi_get_sim_time(uint32_t *high, uint32_t *low)
{
    vhpiTimeT vhpi_time_s;
    vhpi_get_time(&vhpi_time_s, NULL);
    check_vhpi_error();
    *high = vhpi_time_s.high;
    *low = vhpi_time_s.low;
}

// Value related functions
void gpi_set_signal_value_int(gpi_sim_hdl gpi_hdl, int value)
{
    FENTER
    vhpiValueT  value_s;
    value_s.format = vhpiIntVal;
    value_s.value.intg = value;

    vhpi_put_value((vhpiHandleT)(gpi_hdl->sim_hdl), &value_s, vhpiForcePropagate);
    check_vhpi_error();

    FEXIT
}

void gpi_set_signal_value_str(gpi_sim_hdl gpi_hdl, const char *str)
{
    FENTER
    vhpiValueT value_s;
    vhpiValueT *value_p = &value_s;

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

    value_p->bufSize = len;
    value_p->numElems = len;
    value_p->value.str = buff;
    value_p->format = vhpiBinStrVal;

    vhpi_put_value((vhpiHandleT)(gpi_hdl->sim_hdl), &value_s, vhpiForcePropagate);
    check_vhpi_error();
    free(buff);
    FEXIT
}


static char *gpi_copy_name(const char *name)
{
    int len;
    char *result;
    const char null[] = "NULL";

    if (name)
        len = strlen(name) + 1;
    else {
        LOG_CRITICAL("VPI: NULL came back from VPI");
        len = strlen(null);
        name = null;
    }

    result = (char *)malloc(len);
    if (result == NULL) {
        LOG_CRITICAL("VPI: Attempting allocate string buffer failed!");
        len = strlen(null);
        name = null;
    }

    snprintf(result, len, "%s\0", name);

    return result;
}


char *gpi_get_signal_value_binstr(gpi_sim_hdl gpi_hdl)
{
    FENTER
    vhpiValueT value_s = {vhpiBinStrVal};
    vhpiValueT *value_p = &value_s;

    vhpi_get_value((vhpiHandleT)(gpi_hdl->sim_hdl), value_p);
    check_vhpi_error();

    char *result = gpi_copy_name(value_p->value.str);
    FEXIT
    return result;
}

char *gpi_get_signal_name_str(gpi_sim_hdl gpi_hdl)
{
    FENTER
    const char *name = vhpi_get_str(vhpiFullNameP, (vpiHandle)(gpi_hdl->sim_hdl));
    check_vhpi_error();
    char *result = gpi_copy_name(name);
    FEXIT
    return result;
}

char *gpi_get_signal_type_str(gpi_sim_hdl gpi_hdl)
{
    FENTER
    const char *name = vhpi_get_str(vhpiKindStrP, (vpiHandle)(gpi_hdl->sim_hdl));
    check_vhpi_error();
    char *result = gpi_copy_name(name);
    FEXIT
    return result;
}


// Callback related functions
static void handle_vhpi_callback(const vhpiCbDataT *cb_data)
{
    FENTER
    int rv = 0;
    vpiHandle old_cb;

    p_vhpi_cb_user_data user_data;
    user_data = (p_vhpi_cb_user_data)cb_data->user_data;

    if (!user_data)
        LOG_CRITICAL("VPI: Callback data corrupted");

    user_data->state = VHPI_PRE_CALL;
    old_cb = user_data->cb_hdl;
    rv = user_data->gpi_function(user_data->gpi_cb_data);

    if (old_cb == user_data->cb_hdl)
        gpi_deregister_callback(&user_data->gpi_hdl);

    /* A request to delete could have been done
     * inside gpi_function
     */
    if (user_data->state == VHPI_DELETE)
        gpi_destroy_cb_handle(&user_data->gpi_hdl);
    else
        user_data->state = VHPI_POST_CALL;

    FEXIT
    return;
};

/* Allocates memory that will persist for the lifetime of the
 * handle, this may be short or long. A call to create
 * must have a matching call to destroy at some point
 */
gpi_sim_hdl gpi_create_cb_handle(void)
{
    gpi_sim_hdl ret = NULL;
    FENTER

    p_vhpi_cb_user_data user_data = __gpi_alloc_user();
    if (user_data) {
        user_data->state = VHPI_FREE;
        ret = &user_data->gpi_hdl;
    }

    FEXIT
    return ret;
}

/* Destroys the memory associated with the sim handle
 * this can only be called on a handle that has been
 * returned by a call to gpi_create_cb_handle
 */
void gpi_destroy_cb_handle(gpi_sim_hdl gpi_hdl)
{
    /* Check that is has been called, if this has not
     * happend then also close down the sim data as well
     */
    FENTER
    p_vhpi_cb_user_data user_data;
    user_data = gpi_container_of(gpi_hdl, s_vhpi_cb_user_data, gpi_hdl);

    if (user_data->state == VHPI_PRE_CALL) {
        user_data->state = VHPI_DELETE;
    } else {
        gpi_deregister_callback(gpi_hdl);
        __gpi_free_callback(gpi_hdl);
    }
    FEXIT
}

/* Deregister a prior set up callback with the simulator
 * The handle must have been allocated with gpi_create_cb_handle
 * This can be called at any point between
 * gpi_create_cb_handle and gpi_destroy_cb_handle
 */
int gpi_deregister_callback(gpi_sim_hdl gpi_hdl)
{
    p_vhpi_cb_user_data user_data;
    int rc = 1;
    FENTER

    user_data = gpi_container_of(gpi_hdl, s_vhpi_cb_user_data, gpi_hdl);

    if (user_data->cb_hdl) {
        rc = user_data->gpi_cleanup(user_data);
        user_data->cb_hdl = NULL;
    }

    FEXIT
    GPI_RET(rc);
}

// Call when the handle relates to a one time callback
// No need to call vhpi_deregister_cb as the sim will
// do this but do need to destroy the handle
static int gpi_free_one_time(p_vhpi_cb_user_data user_data)
{
    FENTER
    int rc;
    vhpiHandleT cb_hdl = user_data->cb_hdl;
    if (!cb_hdl) {
        LOG_CRITICAL("VPI: passed a NULL pointer : ABORTING");
        exit(1);
    }

    // If the callback has not been called we also need to call
    // remove as well
    if (!user_data->state == VHPI_PRIMED) {
        rc = vhpi_remove_cb(cb_hdl);
        if (!rc) {
            check_vhpi_error();
            return rc;
        }

        rc = vhpi_release_handle(cb_hdl);
        if (!rc) {
            check_vhpi_error();
            return rc;
        }
    }
    FEXIT
    return rc;
}

// Call when the handle relates to recurring callback
// Unregister must be called when not needed and this
// will clean all memory allocated by the sim
static int gpi_free_recurring(p_vhpi_cb_user_data user_data)
{
    FENTER
    int rc;
    vhpiHandleT cb_hdl = user_data->cb_hdl;
    if (!cb_hdl) {
        LOG_CRITICAL("VPI: passed a NULL pointer : ABORTING");
        exit(1);
    }

    rc = vhpi_remove_cb(cb_hdl);
    check_vhpi_error();
    FEXIT
    return rc;
}

/* These functions request a callback to be active with the current
 * handle and associated data. A callback handle needs to have been
 * allocated with gpi_create_cb_handle first
 */

int gpi_register_value_change_callback(gpi_sim_hdl cb,
                                       int (*gpi_function)(void *),
                                       void *gpi_cb_data,
                                       gpi_sim_hdl gpi_hdl)
{
    FENTER
    vhpiCbDataT cb_data_s;
    vhpiTimeT time;

    p_vhpi_cb_user_data user_data;
    int ret;

    user_data = gpi_container_of(cb, s_vhpi_cb_user_data, gpi_hdl);

    user_data->gpi_cb_data = gpi_cb_data;
    user_data->gpi_function = gpi_function;
    user_data->gpi_cleanup = gpi_free_recurring;
    user_data->cb_value.format = vhpiIntVal;

    cb_data_s.reason    = vhpiCbValueChange;
    cb_data_s.cb_rtn    = handle_vhpi_callback;
    cb_data_s.obj       = (vhpiHandleT)(gpi_hdl->sim_hdl);
    cb_data_s.time      = &time;
    cb_data_s.value     = &user_data->cb_value;
    cb_data_s.user_data = (char *)user_data;

    ret = __gpi_register_cb(user_data, &cb_data_s);
    user_data->state = VHPI_PRIMED;

    FEXIT

    return ret;
}


int gpi_register_readonly_callback(gpi_sim_hdl cb,
                                   int (*gpi_function)(void *),
                                   void *gpi_cb_data)
{
    FENTER
    vhpiCbDataT cb_data_s;
    vhpiTimeT time;

    p_vhpi_cb_user_data user_data;
    int ret;

    user_data = gpi_container_of(cb, s_vhpi_cb_user_data, gpi_hdl);

    user_data->gpi_cb_data = gpi_cb_data;
    user_data->gpi_function = gpi_function;
    user_data->gpi_cleanup = gpi_free_one_time;

    cb_data_s.reason    = vhpiCbEndOfTimeStep;
    cb_data_s.cb_rtn    = handle_vhpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = &time;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)user_data;

    ret = __gpi_register_cb(user_data, &cb_data_s);
    user_data->state = VHPI_PRIMED;

    FEXIT

    return ret;
}

int gpi_register_readwrite_callback(gpi_sim_hdl cb,
                                    int (*gpi_function)(void *),
                                    void *gpi_cb_data)
{
    FENTER
    vhpiCbDataT cb_data_s;
    vhpiTimeT time;

    p_vhpi_cb_user_data user_data;
    int ret;

    user_data = gpi_container_of(cb, s_vhpi_cb_user_data, gpi_hdl);

    user_data->gpi_cb_data = gpi_cb_data;
    user_data->gpi_function = gpi_function;
    user_data->gpi_cleanup = gpi_free_one_time;

    cb_data_s.reason    = vhpiCbEndOfProcesses;
    cb_data_s.cb_rtn    = handle_vhpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = &time;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)user_data;

    ret = __gpi_register_cb(user_data, &cb_data_s);
    user_data->state = VHPI_PRIMED;

    FEXIT

    return ret;
}

int gpi_register_nexttime_callback(gpi_sim_hdl cb,
                                   int (*gpi_function)(void *),
                                   void *gpi_cb_data)
{
    FENTER
    vhpiCbDataT cb_data_s;
    vhpiTimeT time;

    p_vhpi_cb_user_data user_data;
    int ret;

    user_data = gpi_container_of(cb, s_vhpi_cb_user_data, gpi_hdl);

    user_data->gpi_cb_data = gpi_cb_data;
    user_data->gpi_function = gpi_function;
    user_data->gpi_cleanup = gpi_free_one_time;

    cb_data_s.reason    = vhpiCbNextTimeStep;
    cb_data_s.cb_rtn    = handle_vhpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = &time;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)user_data;

    ret = __gpi_register_cb(user_data, &cb_data_s);
    user_data->state = VHPI_PRIMED;

    FEXIT

    return ret;
}
int gpi_register_timed_callback(gpi_sim_hdl cb,
                                int (*gpi_function)(void *),
                                void *gpi_cb_data,
                                uint64_t time_ps)
{
    FENTER
    vhpiCbDataT cb_data_s;
    vhpiTimeT time_s;

    p_vhpi_cb_user_data user_data;
    int ret;

    user_data = gpi_container_of(cb, s_vhpi_cb_user_data, gpi_hdl);

    user_data->gpi_cb_data = gpi_cb_data;
    user_data->gpi_function = gpi_function;
    user_data->gpi_cleanup = gpi_free_one_time;

    time_s.high = (uint32_t)(time_ps>>32);
    time_s.low  = (uint32_t)(time_ps);

    cb_data_s.reason    = vhpiCbAfterDelay;
    cb_data_s.cb_rtn    = handle_vhpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = &time_s;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)user_data;

    ret = __gpi_register_cb(user_data, &cb_data_s);
    user_data->state = VHPI_PRIMED;

    FEXIT

    return ret;
}

int gpi_register_sim_start_callback(gpi_sim_hdl cb,
                                    int (*gpi_function)(void *),
                                    void *gpi_cb_data)
{
    FENTER

    vhpiCbDataT cb_data_s;
    p_vhpi_cb_user_data user_data;

    user_data = gpi_container_of(cb, s_vhpi_cb_user_data, gpi_hdl);

    user_data->gpi_cb_data = gpi_cb_data;
    user_data->gpi_function = gpi_function;
    user_data->gpi_cleanup = gpi_free_one_time;

    cb_data_s.reason    = vhpiCbStartOfSimulation;
    cb_data_s.cb_rtn    = handle_vhpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = NULL;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)user_data;

    /* We ignore the return value here as VCS does some silly
     * things on comilation that means it tries to run through
     * the vlog_startup_routines and so call this routine
     */
    __gpi_register_cb(user_data, &cb_data_s);
    user_data->state = VHPI_PRIMED;

    FEXIT
    return 0;

}

int gpi_register_sim_end_callback(gpi_sim_hdl cb,
                                  int (*gpi_function)(void *),
                                  void *gpi_cb_data)
{
    FENTER

    vhpiCbDataT cb_data_s;
    p_vhpi_cb_user_data user_data;

    user_data = gpi_container_of(cb, s_vhpi_cb_user_data, gpi_hdl);

    user_data->gpi_cb_data = gpi_cb_data;
    user_data->gpi_function = gpi_function;
    user_data->gpi_cleanup = gpi_free_one_time;

    cb_data_s.reason    = vhpiCbEndOfSimulation;
    cb_data_s.cb_rtn    = handle_vhpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = NULL;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)user_data;

    /* We ignore the return value here as VCS does some silly
     * things on comilation that means it tries to run through
     * the vlog_startup_routines and so call this routine
     */
    __gpi_register_cb(user_data, &cb_data_s);
    user_data->state = VHPI_PRIMED;

    FEXIT
    return 0;

}

int gpi_clock_handler(void *clock)
{
    gpi_clock_hdl hdl = (gpi_clock_hdl)clock;
    gpi_sim_hdl cb_hdl;

    if (hdl->exit || ((hdl->max_cycles != 0) && (hdl->max_cycles == hdl->curr_cycle)))
        return;

    /* Unregister/free the last callback that just fired */
    cb_hdl = hdl->cb_hdl;

    hdl->value = !hdl->value;
    gpi_set_signal_value_int(hdl->clk_hdl, hdl->value);
    gpi_register_timed_callback(cb_hdl, gpi_clock_handler, hdl, hdl->period);
    hdl->curr_cycle++;
}

gpi_sim_hdl gpi_clock_register(gpi_sim_hdl sim_hdl, int period, unsigned int cycles)
{
    FENTER

    gpi_clock_hdl hdl = malloc(sizeof(gpi_clock_t));
    if (!hdl)
        LOG_CRITICAL("VPI: Unable to allocate memory");

    hdl->period = period;
    hdl->value = 0;
    hdl->clk_hdl = sim_hdl;
    hdl->exit = false;
    hdl->max_cycles = cycles;
    hdl->curr_cycle = 0;

    gpi_set_signal_value_int(hdl->clk_hdl, hdl->value);
    hdl->cb_hdl = gpi_create_cb_handle();

    gpi_register_timed_callback(hdl->cb_hdl, gpi_clock_handler, hdl, hdl->period);

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
    gpi_sim_info_t sim_info;
    sim_info.argc = 0;
    sim_info.argv = NULL;
    sim_info.product = gpi_copy_name(vhpi_get_str(vhpiNameP, NULL));
    sim_info.version = gpi_copy_name(vhpi_get_str(vhpiToolVersionP, NULL));
    embed_sim_init(&sim_info);

    free(sim_info.product);
    free(sim_info.version);

    FEXIT
}

void register_initial_callback(void)
{
    FENTER
    sim_init_cb = gpi_create_cb_handle();
    gpi_register_sim_start_callback(sim_init_cb, handle_sim_init, (void *)NULL);
    FEXIT
}

int handle_sim_end(void *gpi_cb_data)
{
    FENTER
    if (sim_finish_cb) {
        sim_finish_cb = NULL;
        /* This means that we have been asked to close */
        embed_sim_event(SIM_FAIL, "Simulator shutdown prematurely");
    } /* Other sise we have already been here from the top down so do not need
         to inform the upper layers that anything has occoured */
    __gpi_free_callback(sim_init_cb);
    FEXIT
}

void register_final_callback(void)
{
    FENTER
    sim_finish_cb = gpi_create_cb_handle();
    gpi_register_sim_end_callback(sim_finish_cb, handle_sim_end, (void *)NULL);
    FEXIT
}


// If the Pything world wants things to shut down then unregister
// the callback for end of sim
void gpi_sim_end(void)
{
    FENTER

    sim_finish_cb = NULL;
    vhpi_control(vhpiFinish);
    check_vhpi_error();
    FEXIT
}


// pre-defined VHPI registration table
void (*vhpi_startup_routines[])(void) = {
    register_embed,
    register_initial_callback,
    register_final_callback,
    0
};
