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
*    * Neither the name of Potential Ventures Ltd not the
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

// TODO:
// Some functions are completely untested (vhpi_get_handle_by_index) and others
// need optimisation.
//
// VHPI seems to run significantly slower than VPI, need to investigate.


#include "gpi_priv.h"
#include <vhpi_user.h>

#define VHPI_CHECKING 1

static gpi_sim_hdl sim_init_cb;
static gpi_sim_hdl sim_finish_cb;

typedef enum vhpi_cb_state_e {
    VHPI_FREE = 0,
    VHPI_PRIMED = 1,
    VHPI_PRE_CALL = 2,
    VHPI_POST_CALL = 3,
    VHPI_DELETE = 4,
} vhpi_cb_state_t;

// callback user data used for VPI callbacks
// (mostly just a thin wrapper around the gpi_callback)
typedef struct t_vhpi_cb {
    vhpiHandleT cb_hdl;
    vhpiValueT cb_value;
    vhpi_cb_state_t state;
    gpi_cb_hdl_t gpi_cb_data;
    int (*vhpi_cleanup)(struct t_vhpi_cb *);
} s_vhpi_cb, *p_vhpi_cb;

// Forward declarations
static int vhpi_deregister_callback(gpi_sim_hdl gpi_hdl);
static void vhpi_destroy_cb_handle(gpi_cb_hdl hdl);

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
    case vhpiCbEndOfProcesses:
        return "vhpiCbEndOfProcesses";
    case vhpiCbLastKnownDeltaCycle:
        return "vhpiCbLastKnownDeltaCycle";
    default:
        return "unknown";
    }
}

static const char * vhpi_format_to_string(int reason)
{
    switch (reason) {
    case vhpiBinStrVal:
        return "vhpiBinStrVal";
    case vhpiOctStrVal:
        return "vhpiOctStrVal";
    case vhpiDecStrVal:
        return "vhpiDecStrVal";
    case vhpiHexStrVal:
        return "vhpiHexStrVal";
    case vhpiEnumVal:
        return "vhpiEnumVal";
    case vhpiIntVal:
        return "vhpiIntVal";
    case vhpiLogicVal:
        return "vhpiLogicVal";
    case vhpiRealVal:
        return "vhpiRealVal";
    case vhpiStrVal:
        return "vhpiStrVal";
    case vhpiCharVal:
        return "vhpiCharVal";
    case vhpiTimeVal:
        return "vhpiTimeVal";
    case vhpiPhysVal:
        return "vhpiPhysVal";
    case vhpiObjTypeVal:
        return "vhpiObjTypeVal";
    case vhpiPtrVal:
        return "vhpiPtrVal";
    case vhpiEnumVecVal:
        return "vhpiEnumVecVal";

    default:
        return "unknown";
    }
}



// Should be run after every VPI call to check error status
static int __check_vhpi_error(const char *func, long line)
{
    int level=0;
#if VHPI_CHECKING
    vhpiErrorInfoT info;
    int loglevel;
    level = vhpi_check_error(&info);
    if (level == 0)
        return 0;

    switch (level) {
        case vhpiNote:
            loglevel = GPIInfo;
            break;
        case vhpiWarning:
            loglevel = GPIWarning;
            break;
        case vhpiError:
            loglevel = GPIError;
            break;
        case vhpiFailure:
        case vhpiSystem:
        case vhpiInternal:
            loglevel = GPICritical;
            break;
    }

    gpi_log("cocotb.gpi", loglevel, __FILE__, func, line,
            "VHPI Error level %d: %s\nFILE %s:%d",
            info.severity, info.message, info.file, info.line);

#endif
    return level;
}

#define check_vhpi_error() \
    __check_vhpi_error(__func__, __LINE__)

static inline int __vhpi_register_cb(p_vhpi_cb user, vhpiCbDataT *cb_data)
{
    /* If the user data already has a callback handle then deregister
     * before getting the new one
     */
    vhpiHandleT new_hdl = vhpi_register_cb(cb_data, vhpiReturnCb);
    int ret = 0;

    if (!new_hdl) {
        LOG_CRITICAL("VHPI: Unable to register callback a handle for VHPI type %s(%d)",
                     vhpi_reason_to_string(cb_data->reason), cb_data->reason);
        check_vhpi_error();
        ret = -1;
    }

    vhpiStateT cbState = vhpi_get(vhpiStateP, new_hdl);
    if (cbState != vhpiEnable) {
        LOG_CRITICAL("VHPI ERROR: Registered callback isn't enabled! Got %d\n", cbState);
    }

    if (user->cb_hdl != NULL) {
        LOG_ERROR("VHPI: Attempt to register a callback that's already registered...\n");
        vhpi_deregister_callback(&user->gpi_cb_data.hdl);
    }

    user->cb_hdl = new_hdl;
    user->state = VHPI_PRIMED;

    return ret;
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
static gpi_sim_hdl vhpi_get_root_handle(const char* name)
{
    FENTER
    vhpiHandleT root;
    vhpiHandleT dut;
    gpi_sim_hdl rv;

    root = vhpi_handle(vhpiRootInst, NULL);
    check_vhpi_error();

    if (!root) {
        LOG_ERROR("VHPI: Attempting to get the root handle failed");
        FEXIT
        return NULL;
    }

    if (name)
        dut = vhpi_handle_by_name(name, NULL);
    else
        dut = vhpi_handle(vhpiDesignUnit, root);
    check_vhpi_error();

    if (!dut) {
        LOG_ERROR("VHPI: Attempting to get the DUT handle failed");
        FEXIT
        return NULL;
    }

    const char *found = vhpi_get_str(vhpiNameP, dut);
    check_vhpi_error();

    if (name != NULL && strcmp(name, found)) {
        LOG_WARN("VHPI: Root '%s' doesn't match requested toplevel %s", found, name);
        FEXIT
        return NULL;
    }

    rv = gpi_create_handle();
    rv->sim_hdl = dut;

    FEXIT
    return rv;
}


static gpi_sim_hdl vhpi_get_handle_by_name(const char *name, gpi_sim_hdl parent)
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
static gpi_sim_hdl vhpi_get_handle_by_index(gpi_sim_hdl parent, uint32_t index)
{
    FENTER
    gpi_sim_hdl rv;
    vhpiHandleT obj;

    obj = vhpi_handle_by_index(vhpiParamDecls, (vhpiHandleT)(parent->sim_hdl), index);
    if (!obj) {
        LOG_ERROR("VHPI: Handle idx '%d' not found!", index);
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
static gpi_iterator_hdl vhpi_iterate_hdl(uint32_t type, gpi_sim_hdl base) {
    FENTER

    vhpiHandleT iterator;

    iterator = vhpi_iterator(type, (vhpiHandleT)(base->sim_hdl));
    check_vhpi_error();

    FEXIT
    return (gpi_iterator_hdl)iterator;
}

// Returns NULL when there are no more objects
static gpi_sim_hdl vhpi_next_hdl(gpi_iterator_hdl iterator)
{
    FENTER
    gpi_sim_hdl rv = gpi_create_handle();

    rv->sim_hdl = vhpi_scan((vhpiHandleT) iterator);
    check_vhpi_error();
    if (!rv->sim_hdl) {
        gpi_free_handle(rv);
        rv = NULL;
    }
    FEXIT
    return rv;
}

static void vhpi_get_sim_time(uint32_t *high, uint32_t *low)
{
    vhpiTimeT vhpi_time_s;
    vhpi_get_time(&vhpi_time_s, NULL);
    check_vhpi_error();
    *high = vhpi_time_s.high;
    *low = vhpi_time_s.low;
}

// Value related functions
static vhpiEnumT chr2vhpi(const char value) {
    switch (value) {
        case '0':
            return vhpi0;
        case '1':
            return vhpi1;
        case 'U':
        case 'u':
            return vhpiU;
        case 'Z':
        case 'z':
            return vhpiZ;
        case 'X':
        case 'x':
            return vhpiX;
        default:
            return vhpiDontCare;
    }
}

// Unfortunately it seems that format conversion is not well supported
// We have to set values using vhpiEnum*
static void vhpi_set_signal_value_int(gpi_sim_hdl gpi_hdl, int value)
{
    FENTER
    vhpiValueT value_s;
    int size, i;

    // Determine the type of object, either scalar or vector
    value_s.format = vhpiObjTypeVal;
    value_s.bufSize = 0;
    value_s.value.str = NULL;

    vhpi_get_value((vhpiHandleT)(gpi_hdl->sim_hdl), &value_s);
    check_vhpi_error();

    switch (value_s.format) {
        case vhpiEnumVal:
        case vhpiLogicVal: {
            value_s.value.enumv = value ? vhpi1 : vhpi0;
            break;
        }

        case vhpiEnumVecVal:
        case vhpiLogicVecVal: {
            size = vhpi_get(vhpiSizeP, (vhpiHandleT)(gpi_hdl->sim_hdl));
            value_s.bufSize = size*sizeof(vhpiEnumT); 
            value_s.value.enumvs = (vhpiEnumT *)malloc(size*sizeof(vhpiEnumT));

            for (i=0; i<size; i++)
                value_s.value.enumvs[size-i-1] = value&(1<<i) ? vhpi1 : vhpi0;

            break;
        }

        default: {
            LOG_CRITICAL("Unable to assign value to %s (%d) format object",
                         vhpi_format_to_string(value_s.format), value_s.format);
        }
    }

    vhpi_put_value((vhpiHandleT)(gpi_hdl->sim_hdl), &value_s, vhpiForcePropagate);
    check_vhpi_error();

    if (vhpiEnumVecVal == value_s.format)
        free(value_s.value.enumvs);
    FEXIT
}



// Unfortunately it seems that format conversion is not well supported
// We have to set values using vhpiEnum*
static void vhpi_set_signal_value_str(gpi_sim_hdl gpi_hdl, const char *str)
{
    FENTER
    vhpiValueT value_s;
    int len, size, i;
    const char *ptr;

    // Determine the type of object, either scalar or vector
    value_s.format = vhpiObjTypeVal;
    value_s.bufSize = 0;
    value_s.value.str = NULL;

    vhpi_get_value((vhpiHandleT)(gpi_hdl->sim_hdl), &value_s);
    check_vhpi_error();

    switch (value_s.format) {
        case vhpiEnumVal:
        case vhpiLogicVal: {
            value_s.value.enumv = chr2vhpi(*str);
            break;
        }

        case vhpiEnumVecVal:
        case vhpiLogicVecVal: {
            len = strlen(str);
            size = vhpi_get(vhpiSizeP, (vhpiHandleT)(gpi_hdl->sim_hdl));
            value_s.bufSize = size*sizeof(vhpiEnumT); 
            value_s.value.enumvs = (vhpiEnumT *)malloc(size*sizeof(vhpiEnumT));

            // Initialise to 0s
            for (i=0; i<size; i++)
                value_s.value.enumvs[size-i-1] = vhpi0;

            for (i=0, ptr=str; i<len; ptr++, i++)
                value_s.value.enumvs[i] = chr2vhpi(*ptr);

            break;
        }

        default: {
            LOG_CRITICAL("Unable to assign value to %s (%d) format object",
                         vhpi_format_to_string(value_s.format), value_s.format);
        }
    }

    vhpi_put_value((vhpiHandleT)(gpi_hdl->sim_hdl), &value_s, vhpiForcePropagate);
    check_vhpi_error();
    if(value_s.format == vhpiEnumVecVal)
        free(value_s.value.enumvs);
    FEXIT
}

static char *vhpi_get_signal_value_binstr(gpi_sim_hdl gpi_hdl)
{
    FENTER
    vhpiValueT value_s;
    vhpiValueT *value_p = &value_s;
    char *result;
    size_t size;
    value_p->format = vhpiBinStrVal;


// FIXME Seem to have a problem here
// According to VHPI spec we should call vhpi_get_value once to determine
// how much memory to allocate for the result... it appears that we just
// get bogus values back so we'll use a fixed size buffer for now
#if 0
    // Call once to find out how long the string is
    vhpi_get_value((vhpiHandleT)(gpi_hdl->sim_hdl), value_p);
    check_vhpi_error();

    size = value_p->bufSize;
    LOG_ERROR("After initial call to get value: bufSize=%u", size);
#else
    size = 512;
#endif

    result = (char *)malloc(size);
    if (result == NULL) {
        LOG_CRITICAL("VHPI: Attempting allocate string buffer failed!");
    }

    // Call again to get the value
    value_p->bufSize = size;
    value_p->value.str = result;
    vhpi_get_value((vhpiHandleT)(gpi_hdl->sim_hdl), value_p);
    check_vhpi_error();

    FEXIT
    return result;
}

static char *vhpi_get_signal_name_str(gpi_sim_hdl gpi_hdl)
{
    FENTER
    const char *name = vhpi_get_str(vhpiFullNameP, (vhpiHandleT)(gpi_hdl->sim_hdl));
    check_vhpi_error();
    char *result = gpi_copy_name(name);
    FEXIT
    return result;
}

static char *vhpi_get_signal_type_str(gpi_sim_hdl gpi_hdl)
{
    FENTER
    const char *name = vhpi_get_str(vhpiKindStrP, (vhpiHandleT)(gpi_hdl->sim_hdl));
    check_vhpi_error();
    char *result = gpi_copy_name(name);
    FEXIT
    return result;
}


// Callback related functions
static void handle_vhpi_callback(const vhpiCbDataT *cb_data)
{
    FENTER
    vhpiHandleT old_cb;

    p_vhpi_cb user_data;
    user_data = (p_vhpi_cb)cb_data->user_data;

    if (!user_data)
        LOG_CRITICAL("VHPI: Callback data corrupted");

    user_data->state = VHPI_PRE_CALL;
    old_cb = user_data->cb_hdl;
    gpi_handle_callback(&user_data->gpi_cb_data.hdl);

    if (old_cb == user_data->cb_hdl) {

        // Don't de-register recurring callbacks - VHPI only seems to allow
        // a single registration per recurring callback.  For edge events on
        // signals etc. we never want to remove.
        vhpiStateT cbState = vhpi_get(vhpiStateP, user_data->cb_hdl);
        if (vhpiMature == cbState)
            gpi_deregister_callback(&user_data->gpi_cb_data.hdl);
    }

    /* A request to delete could have been done
     * inside gpi_function
     */
    if (user_data->state == VHPI_DELETE)
        gpi_free_cb_handle(&user_data->gpi_cb_data.hdl);
    else
        user_data->state = VHPI_POST_CALL;

    FEXIT
    return;
};

/* Allocates memory that will persist for the lifetime of the
 * handle, this may be short or long. A call to create
 * must have a matching call to destroy at some point
 */
static gpi_cb_hdl vhpi_create_cb_handle(void)
{
    gpi_cb_hdl ret = NULL;
    FENTER
    p_vhpi_cb user_data = calloc(1, sizeof(*user_data));

    if (user_data)
        ret = &user_data->gpi_cb_data;

    FEXIT
    return ret;
}

/* Destroys the memory associated with the sim handle
 * this can only be called on a handle that has been
 * returned by a call to gpi_create_cb_handle
 */
static void vhpi_destroy_cb_handle(gpi_cb_hdl hdl)
{
    /* Check that is has been called, if this has not
     * happend then also close down the sim data as well
     */
    FENTER
    p_vhpi_cb user_data = gpi_container_of(hdl, s_vhpi_cb, gpi_cb_data);

    free(user_data);
    FEXIT
}


static void *vhpi_get_callback_data(gpi_sim_hdl gpi_hdl)
{
    FENTER
    gpi_cb_hdl gpi_user_data;
    gpi_user_data = gpi_container_of(gpi_hdl, gpi_cb_hdl_t, hdl);
    return gpi_user_data->gpi_cb_data;
}


/* Deregister a prior set up callback with the simulator
 * The handle must have been allocated with gpi_create_cb_handle
 * This can be called at any point between
 * gpi_create_cb_handle and gpi_free_cb_handle
 */
static int vhpi_deregister_callback(gpi_sim_hdl gpi_hdl)
{
    FENTER
    p_vhpi_cb vhpi_user_data;
    gpi_cb_hdl gpi_user_data;
    int rc = 1;

    gpi_user_data = gpi_container_of(gpi_hdl, gpi_cb_hdl_t, hdl);
    vhpi_user_data = gpi_container_of(gpi_user_data, s_vhpi_cb, gpi_cb_data);

    if (vhpi_user_data->cb_hdl != NULL) {
        rc = vhpi_user_data->vhpi_cleanup(vhpi_user_data);
        vhpi_user_data->cb_hdl = NULL;
    }

    FEXIT
    GPI_RET(rc);
}

// Call when the handle relates to a one time callback
// No need to call vhpi_deregister_cb as the sim will
// do this but do need to destroy the handle
static int vhpi_free_one_time(p_vhpi_cb user_data)
{
    FENTER
    int rc = 0;
    vhpiHandleT cb_hdl = user_data->cb_hdl;
    if (!cb_hdl) {
        LOG_CRITICAL("VHPI: passed a NULL pointer : ABORTING");
        exit(1);
    }

    // If the callback has not been called we also need to call
    // remove as well
    if (user_data->state == VHPI_PRIMED) {
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
static int vhpi_free_recurring(p_vhpi_cb user_data)
{
    FENTER
    int rc;
    vhpiHandleT cb_hdl = user_data->cb_hdl;
    if (!cb_hdl) {
        LOG_CRITICAL("VHPI: passed a NULL pointer : ABORTING");
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

static int vhpi_register_value_change_callback(gpi_sim_hdl cb,
                                               int (*gpi_function)(void *),
                                               void *gpi_cb_data,
                                               gpi_sim_hdl gpi_hdl)
{
    FENTER
    
    int ret;
    vhpiCbDataT cb_data_s;
    vhpiTimeT time;
    p_vhpi_cb vhpi_user_data;    
    gpi_cb_hdl gpi_user_data;

    gpi_user_data = gpi_container_of(cb, gpi_cb_hdl_t, hdl);
    vhpi_user_data = gpi_container_of(gpi_user_data, s_vhpi_cb, gpi_cb_data);

    vhpi_user_data->vhpi_cleanup = vhpi_free_recurring;
    vhpi_user_data->cb_value.format = vhpiIntVal;

    cb_data_s.reason    = vhpiCbValueChange;
    cb_data_s.cb_rtn    = handle_vhpi_callback;
    cb_data_s.obj       = (vhpiHandleT)(gpi_hdl->sim_hdl);
    cb_data_s.time      = &time;
    cb_data_s.value     = &vhpi_user_data->cb_value;
    cb_data_s.user_data = (char *)vhpi_user_data;

    ret = __vhpi_register_cb(vhpi_user_data, &cb_data_s);
    
    FEXIT

    return ret;
}


static int vhpi_register_readonly_callback(gpi_sim_hdl cb,
                                           int (*gpi_function)(void *),
                                           void *gpi_cb_data)
{
    FENTER

    int ret;
    vhpiCbDataT cb_data_s;
    vhpiTimeT time;
    p_vhpi_cb vhpi_user_data;
    gpi_cb_hdl gpi_user_data;

    gpi_user_data = gpi_container_of(cb, gpi_cb_hdl_t, hdl);
    vhpi_user_data = gpi_container_of(gpi_user_data, s_vhpi_cb, gpi_cb_data);

    vhpi_user_data->vhpi_cleanup = vhpi_free_one_time;

    cb_data_s.reason    = vhpiCbLastKnownDeltaCycle;
    cb_data_s.cb_rtn    = handle_vhpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = &time;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)vhpi_user_data;

    ret = __vhpi_register_cb(vhpi_user_data, &cb_data_s);
    
    FEXIT

    return ret;
}

static int vhpi_register_readwrite_callback(gpi_sim_hdl cb,
                                            int (*gpi_function)(void *),
                                            void *gpi_cb_data)
{
    FENTER
    
    
    int ret;
    vhpiCbDataT cb_data_s;
    vhpiTimeT time;
    p_vhpi_cb vhpi_user_data;
    gpi_cb_hdl gpi_user_data;

    gpi_user_data = gpi_container_of(cb, gpi_cb_hdl_t, hdl);
    vhpi_user_data = gpi_container_of(gpi_user_data, s_vhpi_cb, gpi_cb_data);

    vhpi_user_data->vhpi_cleanup = vhpi_free_one_time;

    cb_data_s.reason    = vhpiCbEndOfProcesses;
    cb_data_s.cb_rtn    = handle_vhpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = &time;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)vhpi_user_data;

    ret = __vhpi_register_cb(vhpi_user_data, &cb_data_s);
    
    FEXIT

    return ret;
}

static int vhpi_register_nexttime_callback(gpi_sim_hdl cb,
                                          int (*gpi_function)(void *),
                                          void *gpi_cb_data)
{
    FENTER

    int ret;
    vhpiCbDataT cb_data_s;
    vhpiTimeT time;
    p_vhpi_cb vhpi_user_data;
    gpi_cb_hdl gpi_user_data;

    gpi_user_data = gpi_container_of(cb, gpi_cb_hdl_t, hdl);
    vhpi_user_data = gpi_container_of(gpi_user_data, s_vhpi_cb, gpi_cb_data);

    vhpi_user_data->vhpi_cleanup = vhpi_free_one_time;

    cb_data_s.reason    = vhpiCbNextTimeStep;
    cb_data_s.cb_rtn    = handle_vhpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = &time;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)vhpi_user_data;

    ret = __vhpi_register_cb(vhpi_user_data, &cb_data_s);

    FEXIT

    return ret;
}

static int vhpi_register_timed_callback(gpi_sim_hdl cb,
                                       int (*gpi_function)(void *),
                                       void *gpi_cb_data,
                                       uint64_t time_ps)
{
    FENTER
    
    int ret;
    vhpiCbDataT cb_data_s;
    vhpiTimeT time_s;
    p_vhpi_cb vhpi_user_data;
    gpi_cb_hdl gpi_user_data;

    gpi_user_data = gpi_container_of(cb, gpi_cb_hdl_t, hdl);
    vhpi_user_data = gpi_container_of(gpi_user_data, s_vhpi_cb, gpi_cb_data);

    vhpi_user_data->vhpi_cleanup = vhpi_free_one_time;

    time_s.high = (uint32_t)(time_ps>>32);
    time_s.low  = (uint32_t)(time_ps);

    cb_data_s.reason    = vhpiCbAfterDelay;
    cb_data_s.cb_rtn    = handle_vhpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = &time_s;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)vhpi_user_data;

    ret = __vhpi_register_cb(vhpi_user_data, &cb_data_s);

    FEXIT

    return ret;
}


// If the Pything world wants things to shut down then unregister
// the callback for end of sim
static void vhpi_sim_end(void)
{
    FENTER

    sim_finish_cb = NULL;
    vhpi_control(vhpiFinish);
    check_vhpi_error();
    FEXIT
}

static s_gpi_impl_tbl vhpi_table = {
    .sim_end = vhpi_sim_end,
    .iterate_handle = vhpi_iterate_hdl,
    .next_handle = vhpi_next_hdl,
    .create_cb_handle = vhpi_create_cb_handle,
    .destroy_cb_handle = vhpi_destroy_cb_handle,
    .deregister_callback = vhpi_deregister_callback,
    .get_root_handle = vhpi_get_root_handle,
    .get_sim_time = vhpi_get_sim_time,
    .get_handle_by_name = vhpi_get_handle_by_name,
    .get_handle_by_index = vhpi_get_handle_by_index,
    .get_signal_name_str = vhpi_get_signal_name_str,
    .get_signal_type_str = vhpi_get_signal_type_str,
    .get_signal_value_binstr = vhpi_get_signal_value_binstr,
    .set_signal_value_int = vhpi_set_signal_value_int,
    .set_signal_value_str = vhpi_set_signal_value_str,
    .register_timed_callback = vhpi_register_timed_callback,
    .register_readwrite_callback = vhpi_register_readwrite_callback,
    .register_nexttime_callback = vhpi_register_nexttime_callback,
    .register_value_change_callback = vhpi_register_value_change_callback,
    .register_readonly_callback = vhpi_register_readonly_callback,
    .get_callback_data = vhpi_get_callback_data,
};

static void register_embed(void)
{
    FENTER
    gpi_register_impl(&vhpi_table, 0xfeed);
    gpi_embed_init_python();
    FEXIT
}


static int handle_sim_init(void *gpi_cb_data)
{
    FENTER
    gpi_sim_info_t sim_info;
    sim_info.argc = 0;
    sim_info.argv = NULL;
    sim_info.product = gpi_copy_name(vhpi_get_str(vhpiNameP, NULL));
    sim_info.version = gpi_copy_name(vhpi_get_str(vhpiToolVersionP, NULL));
    gpi_embed_init(&sim_info);

    free(sim_info.product);
    free(sim_info.version);

    FEXIT

    return 0;
}

static void register_initial_callback(void)
{
    FENTER

    vhpiCbDataT cb_data_s;
    p_vhpi_cb vhpi_user_data;
    gpi_cb_hdl gpi_user_data;


    sim_init_cb = gpi_create_cb_handle();

    gpi_user_data = gpi_container_of(sim_init_cb, gpi_cb_hdl_t, hdl);
    vhpi_user_data = gpi_container_of(gpi_user_data, s_vhpi_cb, gpi_cb_data);

    gpi_user_data->gpi_cb_data = NULL;
    gpi_user_data->gpi_function = handle_sim_init;
    
    vhpi_user_data->vhpi_cleanup = vhpi_free_one_time;
    
    cb_data_s.reason    = vhpiCbStartOfSimulation;
    cb_data_s.cb_rtn    = handle_vhpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = NULL;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)vhpi_user_data;

    __vhpi_register_cb(vhpi_user_data, &cb_data_s);

    FEXIT
}

static int handle_sim_end(void *gpi_cb_data)
{
    FENTER
    if (sim_finish_cb) {
        sim_finish_cb = NULL;
        /* This means that we have been asked to close */
        embed_sim_event(SIM_FAIL, "Simulator shutdown prematurely");
    } /* Other sise we have already been here from the top down so do not need
         to inform the upper layers that anything has occoured */
    gpi_free_cb_handle(sim_init_cb);
    FEXIT

    return 0;
}

static void register_final_callback(void)
{
    FENTER
    
    vhpiCbDataT cb_data_s;
    p_vhpi_cb vhpi_user_data;
    gpi_cb_hdl gpi_user_data;

    sim_finish_cb = gpi_create_cb_handle();

    gpi_user_data = gpi_container_of(sim_finish_cb, gpi_cb_hdl_t, hdl);
    vhpi_user_data = gpi_container_of(gpi_user_data, s_vhpi_cb, gpi_cb_data);

    gpi_user_data->gpi_cb_data = NULL;
    gpi_user_data->gpi_function = handle_sim_end;
    vhpi_user_data->vhpi_cleanup = vhpi_free_one_time;

    cb_data_s.reason    = vhpiCbEndOfSimulation;
    cb_data_s.cb_rtn    = handle_vhpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = NULL;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char *)vhpi_user_data;

    /* We ignore the return value here as VCS does some silly
     * things on comilation that means it tries to run through
     * the vlog_startup_routines and so call this routine
     */
    __vhpi_register_cb(vhpi_user_data, &cb_data_s);

    FEXIT
}

// pre-defined VHPI registration table
void (*vhpi_startup_routines[])(void) = {
    register_embed,
    register_initial_callback,
    register_final_callback,
    0
};

// For non-VPI compliant applications that cannot find vlog_startup_routines
void vhpi_startup_routines_bootstrap(void) {
    void (*routine)(void);
    int i;
    routine = vhpi_startup_routines[0];
    for (i = 0, routine = vhpi_startup_routines[i];
         routine;
         routine = vhpi_startup_routines[++i]) {
        routine();
    }
}
