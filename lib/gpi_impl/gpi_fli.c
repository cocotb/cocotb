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

#include "gpi_priv.h"
#include <mti.h>

#define FLII_CHECKING 1

static gpi_sim_hdl sim_init_cb;
static gpi_sim_hdl sim_finish_cb;


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
static gpi_sim_hdl fli_get_root_handle(const char* name)
{
    FENTER
    mtiRegionIdT root;
    gpi_sim_hdl rv;

    for (root = mti_GetTopRegion(); root != NULL; root = mti_NextRegion(root)) {
        if (name == NULL || !strcmp(name, mti_GetRegionName(root)))
            break;
    }

    if (!root) {
        goto error;
    }

    rv = gpi_create_handle();
    rv->sim_hdl = (void *)root;

    FEXIT
    return rv;

  error:

    LOG_CRITICAL("FPI: Couldn't find root handle %s", name);

    for (root = mti_GetTopRegion(); root != NULL; root = mti_NextRegion(root)) {

        LOG_CRITICAL("FLI: Toplevel instances: %s != %s...", name, mti_GetRegionName(root));

        if (name == NULL)
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
static gpi_sim_hdl fli_get_handle_by_name(const char *name, gpi_sim_hdl parent)
{
    FENTER
    mtiRegionIdT hdl = (mtiRegionIdT)parent->sim_hdl;
    gpi_sim_hdl rv;
    void *result;
    mtiRegionIdT result_reg;
    mtiSignalIdT result_sig;
    mtiVariableIdT result_var;
    size_t baselen = strlen(mti_GetRegionFullName(hdl));
    char *fullname;
    char *ptr;

    fullname = (char *)malloc(baselen + strlen(name) + 2);

    if (fullname == NULL) {
        LOG_CRITICAL("FLI: Attempting allocate string buffer failed!");
        return NULL;
    }

    strncpy(fullname, mti_GetRegionFullName(hdl), baselen);
    ptr = fullname + baselen;
    *ptr++ = '/';
    strncpy(ptr, name, strlen(name));

    result_reg = mti_FindRegion(fullname);
    result = (void *)result_reg;
    if (result_reg) goto success;
//     result = mti_FindPort(fullname);
//     if (result) goto success;
    result_sig = mti_FindSignal(fullname);
    result = (void *)result_sig;
    if (result_sig) goto success;
    result_var = mti_FindVar(fullname);
    result = (void *)result_var;
    if (result) goto success;

error:
    LOG_DEBUG("FLII: Handle '%s' not found!", name);

    // NB we deliberately don't dump an error message here because it's
    // a valid use case to attempt to grab a signal by name - for example
    // optional signals on a bus.
    free(fullname);
    return NULL;

success:
    free(fullname);
    rv = gpi_create_handle();
    rv->sim_hdl = result;

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
static gpi_sim_hdl fli_get_handle_by_index(gpi_sim_hdl parent, uint32_t index)
{
    FENTER
    LOG_ERROR("FLI: Obtaining a handle by index not supported by FLI?");
    FEXIT
    return NULL;
}


// Functions for iterating over entries of a handle
// Returns an iterator handle which can then be used in gpi_next calls
// NB May return NULL if no objects of the request type exist
static gpi_iterator_hdl fli_iterate_hdl(uint32_t type, gpi_sim_hdl base) {
    FENTER
    LOG_ERROR("FLI: Iterating over a handle not implemented yet");
    FEXIT
    return NULL;
}

// Returns NULL when there are no more objects
static gpi_sim_hdl fli_next_hdl(gpi_iterator_hdl iterator)
{
    FENTER
    LOG_ERROR("FLI: Iterating over a handle not implemented yet");
    FEXIT
    return NULL;
}

static void fli_get_sim_time(uint32_t *high, uint32_t *low)
{
    *high = mti_NowUpper();
    *low = mti_Now();
}

// Value related functions
static void fli_set_signal_value_int(gpi_sim_hdl gpi_hdl, int value)
{
    FENTER
    LOG_ERROR("Attempt to force signal %s failed (not implemented)", 
                mti_GetSignalName((mtiSignalIdT)gpi_hdl->sim_hdl));
    FEXIT
}

static void fli_set_signal_value_str(gpi_sim_hdl gpi_hdl, const char *str)
{
    FENTER
    char * str_copy = strdup(str);              // Mentor discard const qualifier
    int rc = mti_ForceSignal((mtiSignalIdT)(gpi_hdl->sim_hdl),
                             str_copy,
                             -1,                // If the delay parameter is negative,
                                                // then the force is applied immediately.
                             MTI_FORCE_DEPOSIT,
                             -1,                // cancel_period
                             -1);               // repeat_period

    if (!rc)
        LOG_ERROR("Attempt to force signal %s failed", 
                    mti_GetSignalName((mtiSignalIdT)gpi_hdl->sim_hdl));
    free(str_copy);
    FEXIT
}

static char *fli_get_signal_value_binstr(gpi_sim_hdl gpi_hdl)
{
    FENTER
    mtiInt32T value;
    switch (mti_GetTypeKind(mti_GetSignalType((mtiSignalIdT)gpi_hdl->sim_hdl))){
        case MTI_TYPE_SCALAR:
        case MTI_TYPE_ENUM:
        case MTI_TYPE_PHYSICAL:
            value = mti_GetSignalValue((mtiSignalIdT)gpi_hdl->sim_hdl);
            break;
        default:
            mti_PrintFormatted( "(Type not supported)\n" );
            break;
    }
    char *result;// = gpi_copy_name(value_p->value.str);
    FEXIT
    return result;
}

static char *fli_get_signal_name_str(gpi_sim_hdl gpi_hdl)
{
    FENTER
    const char *name = mti_GetSignalName((mtiSignalIdT)gpi_hdl->sim_hdl);
    char *result = gpi_copy_name(name);
    FEXIT
    return result;
}

static char *fli_get_signal_type_str(gpi_sim_hdl gpi_hdl)
{
    switch (mti_GetTypeKind(mti_GetSignalType((mtiSignalIdT)gpi_hdl->sim_hdl))){
        case MTI_TYPE_SCALAR   : return strdup("Scalar");
        case MTI_TYPE_ARRAY    : return strdup("Array");
        case MTI_TYPE_RECORD   : return strdup("Record");
        case MTI_TYPE_ENUM     : return strdup("Enum");
        case MTI_TYPE_INTEGER  : return strdup("Integer");
        case MTI_TYPE_PHYSICAL : return strdup("Physical");
        case MTI_TYPE_REAL     : return strdup("Real");
        case MTI_TYPE_ACCESS   : return strdup("Access");
        case MTI_TYPE_FILE     : return strdup("File");
        case MTI_TYPE_TIME     : return strdup("Time");
        case MTI_TYPE_C_REAL   : return strdup("C Real");
        case MTI_TYPE_C_ENUM   : return strdup("C Enum");
        default                : return strdup("Unknown!");
    }
}


// Callback related functions
static int32_t handle_fli_callback(gpi_cb_hdl cb_data)
{
    FENTER
    LOG_CRITICAL("FLI: Callbacks not implemented yet");
    FEXIT
    return 0;
};


static int fli_deregister_callback(gpi_sim_hdl gpi_hdl)
{
    FENTER
    LOG_CRITICAL("FLI: Callbacks not implemented yet");
    FEXIT
    return 0;
}


/* These functions request a callback to be active with the current
 * handle and associated data. A callback handle needs to have been
 * allocated with gpi_create_cb_handle first
 */
static int fli_register_value_change_callback(gpi_sim_hdl cb,
                                              int (*gpi_function)(void *),
                                              void *gpi_cb_data,
                                              gpi_sim_hdl gpi_hdl)
{
    FENTER
    FEXIT
    return 0;
}

static int fli_register_readonly_callback(gpi_sim_hdl cb,
                                          int (*gpi_function)(void *),
                                          void *gpi_cb_data)
{
    FENTER
    FEXIT
    return 0;
}

static int fli_register_readwrite_callback(gpi_sim_hdl cb,
                                           int (*gpi_function)(void *),
                                           void *gpi_cb_data)
{
    FENTER
    FEXIT
    return 0;
}



static int fli_register_nexttime_callback(gpi_sim_hdl cb,
                                          int (*gpi_function)(void *),
                                          void *gpi_cb_data)
{
    FENTER
    FEXIT
    return 0;
}

static int fli_register_timed_callback(gpi_sim_hdl cb,
                                       int (*gpi_function)(void *),
                                       void *gpi_cb_data,
                                       uint64_t time_ps)
{
    FENTER
    FEXIT
    return 0;
}

static void fli_sim_end(void)
{
    sim_finish_cb = NULL;
    mti_Quit();
}


/* Checking of validity is done in the common code */
static gpi_cb_hdl fli_create_cb_handle(void)
{
    gpi_cb_hdl ret = NULL;

    FENTER

    void * new_cb_hdl = calloc(1, sizeof(*new_cb_hdl));
    if (new_cb_hdl)
        ret = &new_cb_hdl->gpi_cb_data;

    FEXIT
    return ret;
}



static s_gpi_impl_tbl fli_table = {
    .sim_end = fli_sim_end,
    .iterate_handle = fli_iterate_hdl,
    .next_handle = fli_next_hdl,
    .create_cb_handle = fli_create_cb_handle,
    .destroy_cb_handle = fli_destroy_cb_handle,
    .deregister_callback = fli_deregister_callback,
    .get_root_handle = fli_get_root_handle,
    .get_sim_time = fli_get_sim_time,
    .get_handle_by_name = fli_get_handle_by_name,
    .get_handle_by_index = fli_get_handle_by_index,
    .get_signal_name_str = fli_get_signal_name_str,
    .get_signal_type_str = fli_get_signal_type_str,
    .get_signal_value_binstr = fli_get_signal_value_binstr,
    .set_signal_value_int = fli_set_signal_value_int,
    .set_signal_value_str = fli_set_signal_value_str,
    .register_timed_callback = fli_register_timed_callback,
    .register_readwrite_callback = fli_register_readwrite_callback,
    .register_nexttime_callback = fli_register_nexttime_callback,
    .register_value_change_callback = fli_register_value_change_callback,
    .register_readonly_callback = fli_register_readonly_callback,
    .get_callback_data = fli_get_callback_data,
};

static void register_embed(void)
{
    gpi_register_impl(&fli_table, 0xfe70);
    gpi_embed_init_python();
}


// No access to plusargs via FLI?
static int handle_sim_init(void *gpi_cb_data)
{
    FENTER
    gpi_sim_info_t sim_info;
    sim_info.argc = NULL;
    sim_info.argv = NULL;
    sim_info.product = mti_GetProductVersion();
    sim_info.version = NULL;
    gpi_embed_init(&sim_info);
    FEXIT
}

static void register_initial_callback(void)
{
    FENTER
    gpi_cb_hdl gpi_user_data;
    sim_init_cb = gpi_create_cb_handle();
    gpi_user_data = gpi_container_of(sim_init_cb, gpi_cb_hdl_t, hdl);

    gpi_user_data->gpi_cb_data = NULL;
    gpi_user_data->gpi_function = handle_sim_init;

    mti_AddLoadDoneCB(handle_fli_callback, &gpi_user_data);
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
}

static void register_final_callback(void)
{
    FENTER
    gpi_cb_hdl gpi_user_data;
    sim_init_cb = gpi_create_cb_handle();
    gpi_user_data = gpi_container_of(sim_init_cb, gpi_cb_hdl_t, hdl);

    gpi_user_data->gpi_cb_data = NULL;
    gpi_user_data->gpi_function = handle_sim_end;

    mti_AddQuitCB(handle_fli_callback, &gpi_user_data);
    FEXIT
}


// Initialisation needs to be triggered from a foreign architecture in the RTL
//
// ATTRIBUTE foreign OF blah : ARCHITECTURE IS "cocotb_init libgpi.so; parameter";
void cocotb_init(mtiRegionIdT region,
                    char *param,
                    mtiInterfaceListT *generics,
                    mtiInterfaceListT *ports)
{
    register_embed();
    register_initial_callback();
    register_final_callback();
}


