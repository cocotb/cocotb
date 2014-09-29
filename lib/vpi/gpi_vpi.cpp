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

#include "../gpi/gpi_priv.h"
#include <vpi_user.h>

#define VPI_CHECKING 1

extern "C" { 
int32_t handle_vpi_callback(p_cb_data cb_data);
int __check_vpi_error(const char *func, long line);
}


// Should be run after every VPI call to check error status
int __check_vpi_error(const char *func, long line)
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

#define check_vpi_error() do { \
    __check_vpi_error(__func__, __LINE__); \
} while (0)

typedef enum vpi_cb_state_e {
    VPI_FREE = 0,
    VPI_PRIMED = 1,
    VPI_PRE_CALL = 2,
    VPI_POST_CALL = 3,
    VPI_DELETE = 4,
} vpi_cb_state_t;

class vpi_obj_hdl : public gpi_obj_hdl {
public:
    vpi_obj_hdl(vpiHandle hdl, gpi_impl_interface *impl) : gpi_obj_hdl(impl),
                                                           vpi_hdl(hdl) { }
public:
    vpiHandle vpi_hdl;

};

class vpi_cb_hdl : public gpi_cb_hdl {
public:
    vpiHandle vpi_hdl;
    vpi_cb_state_t state;

public:
    vpi_cb_hdl(gpi_impl_interface *impl) : gpi_cb_hdl(impl),
                                           vpi_hdl(NULL) { }

protected:
    /* If the user data already has a callback handle then deregister
     * before getting the new one
     */
    int register_cb(p_cb_data cb_data) {
        if (state == VPI_PRIMED) {
            fprintf(stderr,
                    "Attempt to prime an already primed trigger for %s!\n", 
                    vpi_reason_to_string(cb_data->reason));
        }

        if (vpi_hdl != NULL) {
            fprintf(stderr,
                    "We seem to already be registered, deregistering %s!\n",
                    vpi_reason_to_string(cb_data->reason));

            cleanup_callback();
        }

        vpiHandle new_hdl = vpi_register_cb(cb_data);
        int ret = 0;

        if (!new_hdl) {
            LOG_CRITICAL("VPI: Unable to register callback a handle for VPI type %s(%d)",
                         vpi_reason_to_string(cb_data->reason), cb_data->reason);
            check_vpi_error();
            ret = -1;
        }

        vpi_hdl = new_hdl;
        state = VPI_PRIMED;

        return ret;
    }

    const char *vpi_reason_to_string(int reason)
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

};

class vpi_onetime_cb : public vpi_cb_hdl {
public:
    vpi_onetime_cb(gpi_impl_interface *impl) : vpi_cb_hdl(impl) { }
    int cleanup_callback(void) {
        FENTER
        int rc;
        if (!vpi_hdl) {
            LOG_CRITICAL("VPI: passed a NULL pointer : ABORTING");
            exit(1);
        }

        // If the callback has not been called we also need to call
        // remove as well
        if (state == VPI_PRIMED) {

            rc = vpi_remove_cb(vpi_hdl);
            if (!rc) {
                check_vpi_error();
                return rc;
            }
            vpi_hdl = NULL;

    // HACK: Calling vpi_free_object after vpi_remove_cb causes Modelsim to VPIEndOfSimulationCallback
    #if 0
            rc = vpi_free_object(cb_hdl);
            if (!rc) {
                check_vpi_error();
                return rc;
            }
    #endif
        }
        state = VPI_FREE;
        return rc;
    }
};

class vpi_recurring_cb : public vpi_cb_hdl {
public:
    vpi_recurring_cb(gpi_impl_interface *impl) : vpi_cb_hdl(impl) { }
    int cleanup_callback(void) {
        FENTER
        int rc;
        if (!vpi_hdl) {
            LOG_CRITICAL("VPI: passed a NULL pointer : ABORTING");
            exit(1);
        }

        rc = vpi_remove_cb(vpi_hdl);
        check_vpi_error();
        FEXIT
        return rc;
    }
};

class vpi_cb_value_change : public vpi_recurring_cb {
public:
    vpi_cb_value_change(gpi_impl_interface *impl) : vpi_recurring_cb(impl) { }
    int arm_callback(vpi_obj_hdl *vpi_hdl) {
        s_cb_data cb_data_s;
        s_vpi_time vpi_time_s = {.type = vpiSuppressTime };
        s_vpi_value cb_value = {.format = vpiIntVal };

        cb_data_s.reason    = cbValueChange;
        cb_data_s.cb_rtn    = handle_vpi_callback;
        cb_data_s.obj       = vpi_hdl->vpi_hdl;
        cb_data_s.time      = &vpi_time_s;
        cb_data_s.value     = &cb_value;
        cb_data_s.user_data = (char *)this;

        return register_cb(&cb_data_s);
    }
};

class vpi_cb_startup : public vpi_onetime_cb {
public:
    vpi_cb_startup(gpi_impl_interface *impl) : vpi_onetime_cb(impl) { }
    int run_callback(void) {
        s_vpi_vlog_info info;
        gpi_sim_info_t sim_info;

        vpi_get_vlog_info(&info);

        sim_info.argc = info.argc;
        sim_info.argv = info.argv;
        sim_info.product = info.product;
        sim_info.version = info.version;

        gpi_embed_init(&sim_info);

        return 0;
    }

    int arm_callback(void) {
        s_cb_data cb_data_s;

        cb_data_s.reason    = cbStartOfSimulation;
        cb_data_s.cb_rtn    = handle_vpi_callback;
        cb_data_s.obj       = NULL;
        cb_data_s.time      = NULL;
        cb_data_s.value     = NULL;
        cb_data_s.user_data = (char*)this;

        return register_cb(&cb_data_s);
    }
};

class vpi_cb_readonly : public vpi_onetime_cb {
public:
    vpi_cb_readonly(gpi_impl_interface *impl) : vpi_onetime_cb(impl) { }
    int arm_callback(void) {
        s_cb_data cb_data_s;
        s_vpi_time vpi_time_s;

        vpi_time_s.type = vpiSimTime,
        vpi_time_s.low = 0,
        vpi_time_s.high = 0,

        cb_data_s.reason    = cbReadOnlySynch;
        cb_data_s.cb_rtn    = handle_vpi_callback;
        cb_data_s.obj       = NULL;
        cb_data_s.time      = &vpi_time_s;
        cb_data_s.value     = NULL;
        cb_data_s.user_data = (char *)this;

        return register_cb(&cb_data_s);
    }
};


class vpi_cb_shutdown : public vpi_onetime_cb {
public:
    vpi_cb_shutdown(gpi_impl_interface *impl) : vpi_onetime_cb(impl) { }
    int run_callback(void) {
        LOG_WARN("Shutdown called");
        gpi_embed_end();
        return 0;
    }

    int arm_callback(void) {
        s_cb_data cb_data_s;

        cb_data_s.reason    = cbEndOfSimulation;
        cb_data_s.cb_rtn    = handle_vpi_callback;
        cb_data_s.obj       = NULL;
        cb_data_s.time      = NULL;
        cb_data_s.value     = NULL;
        cb_data_s.user_data = (char*)this;

        return register_cb(&cb_data_s);
    }
};

class vpi_cb_timed : public vpi_onetime_cb {
public:
    vpi_cb_timed(gpi_impl_interface *impl) : vpi_onetime_cb(impl) { }

    int arm_callback(uint64_t time_ps) {
        s_cb_data cb_data_s;
        s_vpi_time vpi_time_s;

        vpi_time_s.type = vpiSimTime;
        vpi_time_s.high = (uint32_t)(time_ps>>32);
        vpi_time_s.low  = (uint32_t)(time_ps);

        cb_data_s.reason    = cbAfterDelay;
        cb_data_s.cb_rtn    = handle_vpi_callback;
        cb_data_s.obj       = NULL;
        cb_data_s.time      = &vpi_time_s;
        cb_data_s.value     = NULL;
        cb_data_s.user_data = (char *)this;

        return register_cb(&cb_data_s);
    }
};

class vpi_cb_readwrite : public vpi_onetime_cb {
public:
    vpi_cb_readwrite(gpi_impl_interface *impl) : vpi_onetime_cb(impl) { }

    int arm_callback(void) {
        s_cb_data cb_data_s;
        s_vpi_time vpi_time_s;

        vpi_time_s.type = vpiSimTime;
        vpi_time_s.high = 0;
        vpi_time_s.low = 0;

        cb_data_s.reason    = cbReadWriteSynch;
        cb_data_s.cb_rtn    = handle_vpi_callback;
        cb_data_s.obj       = NULL;
        cb_data_s.time      = &vpi_time_s;
        cb_data_s.value     = NULL;
        cb_data_s.user_data = (char *)this;

        return register_cb(&cb_data_s);
    }
};

class vpi_impl : public gpi_impl_interface {
public:
    vpi_impl(const string& name) : gpi_impl_interface(name) { }

     /* Sim related */
    void sim_end(void);
    void get_sim_time(uint32_t *high, uint32_t *low);

    /* Signal related */
    gpi_obj_hdl *get_root_handle(const char *name);
    gpi_obj_hdl *get_handle_by_name(const char *name, gpi_obj_hdl *parent);
    gpi_obj_hdl *get_handle_by_index(gpi_obj_hdl *parent, uint32_t index);
    void free_handle(gpi_obj_hdl*) { }
    gpi_iterator *iterate_handle(uint32_t type, gpi_obj_hdl *base) { return NULL; }
    gpi_obj_hdl *next_handle(gpi_iterator *iterator) { return NULL; }
    char* get_signal_value_binstr(gpi_obj_hdl *gpi_hdl);
    char* get_signal_name_str(gpi_obj_hdl *gpi_hdl);
    char* get_signal_type_str(gpi_obj_hdl *gpi_hdl);
    void set_signal_value_int(gpi_obj_hdl *gpi_hdl, int value);
    void set_signal_value_str(gpi_obj_hdl *gpi_hdl, const char *str);    // String of binary char(s) [1, 0, x, z]
    
    /* Callback related */
    gpi_cb_hdl *register_timed_callback(uint64_t time_ps);
    gpi_cb_hdl *register_value_change_callback(gpi_obj_hdl *obj_hdl);
    gpi_cb_hdl *register_readonly_callback(void);
    gpi_cb_hdl *register_nexttime_callback(void) { return NULL; }
    gpi_cb_hdl *register_readwrite_callback(void);
    int deregister_callback(gpi_cb_hdl *gpi_hdl);

    gpi_cb_hdl *create_cb_handle(void) { return NULL; }
    void destroy_cb_handle(gpi_cb_hdl *gpi_hdl) { }
};

extern "C" {

static vpi_cb_hdl *sim_init_cb;
static vpi_cb_hdl *sim_finish_cb;
static vpi_impl *vpi_table;

}

void vpi_impl::get_sim_time(uint32_t *high, uint32_t *low)
{
    s_vpi_time vpi_time_s;
    vpi_time_s.type = vpiSimTime;//vpiScaledRealTime;        //vpiSimTime;
    vpi_get_time(NULL, &vpi_time_s);
    check_vpi_error();
    *high = vpi_time_s.high;
    *low = vpi_time_s.low;
}

gpi_obj_hdl *vpi_impl::get_root_handle(const char* name)
{
    FENTER
    vpiHandle root;
    vpiHandle iterator;
    vpi_obj_hdl *rv;

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

    rv = new vpi_obj_hdl(root, this);

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
gpi_obj_hdl *vpi_impl::get_handle_by_name(const char *name, gpi_obj_hdl *parent)
{
    FENTER
    gpi_obj_hdl *rv;
    vpiHandle obj;
    vpiHandle iterator;
    int len;
    char *buff;
    vpi_obj_hdl *vpi_obj = reinterpret_cast<vpi_obj_hdl*>(parent);

    // Structures aren't technically a scope, according to the LRM. If parent
    // is a structure then we have to iterate over the members comparing names
    if (vpiStructVar == vpi_get(vpiType, vpi_obj->vpi_hdl)) {

        iterator = vpi_iterate(vpiMember, vpi_obj->vpi_hdl);

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
    obj = vpi_handle_by_name(buff, vpi_obj->vpi_hdl);
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
    rv = new vpi_obj_hdl(obj, this);

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
gpi_obj_hdl *vpi_impl::get_handle_by_index(gpi_obj_hdl *parent, uint32_t index)
{
    FENTER
    vpiHandle obj;
    gpi_obj_hdl *rv;
    vpi_obj_hdl *vpi_obj = reinterpret_cast<vpi_obj_hdl*>(parent);

    obj = vpi_handle_by_index(vpi_obj->vpi_hdl, index);
    if (!obj) {
        LOG_ERROR("VPI: Handle idx '%d' not found!", index);
        return NULL;
    }

    rv = new vpi_obj_hdl(obj, this);

    FEXIT
    return rv;
}

// Value related functions
void vpi_impl::set_signal_value_int(gpi_obj_hdl *gpi_hdl, int value)
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
    vpi_obj_hdl *vpi_obj = reinterpret_cast<vpi_obj_hdl*>(gpi_hdl);
    vpi_put_value(vpi_obj->vpi_hdl, value_p, vpi_time_p, vpiInertialDelay);
    check_vpi_error();

    FEXIT
}

void vpi_impl::set_signal_value_str(gpi_obj_hdl *gpi_hdl, const char *str)
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
    vpi_obj_hdl *vpi_obj = reinterpret_cast<vpi_obj_hdl*>(gpi_hdl);
    vpi_put_value(vpi_obj->vpi_hdl, value_p, NULL, vpiNoDelay);
    check_vpi_error();
    free(buff);
    FEXIT
}

char *vpi_impl::get_signal_type_str(gpi_obj_hdl *gpi_hdl)
{
    FENTER
    vpi_obj_hdl *vpi_obj = reinterpret_cast<vpi_obj_hdl*>(gpi_hdl);
    const char *name = vpi_get_str(vpiType, vpi_obj->vpi_hdl);
    check_vpi_error();
    char *result = gpi_hdl->gpi_copy_name(name);
    FEXIT
    return result;
}

char *vpi_impl::get_signal_name_str(gpi_obj_hdl *gpi_hdl)
{
    FENTER
    vpi_obj_hdl *vpi_obj = reinterpret_cast<vpi_obj_hdl*>(gpi_hdl);
    const char *name = vpi_get_str(vpiFullName, vpi_obj->vpi_hdl);
    check_vpi_error();
    char *result = gpi_hdl->gpi_copy_name(name);
    FEXIT
    return result;
}

char *vpi_impl::get_signal_value_binstr(gpi_obj_hdl *gpi_hdl)
{
    FENTER
    vpi_obj_hdl *vpi_obj = reinterpret_cast<vpi_obj_hdl*>(gpi_hdl);
    s_vpi_value value_s = {vpiBinStrVal};
    p_vpi_value value_p = &value_s;

    vpi_get_value(vpi_obj->vpi_hdl, value_p);
    check_vpi_error();

    char *result = gpi_hdl->gpi_copy_name(value_p->value.str);
    FEXIT
    return result;
}

gpi_cb_hdl *vpi_impl::register_timed_callback(uint64_t time_ps)
{
    FENTER

    vpi_cb_timed *hdl = new vpi_cb_timed(vpi_table);

    if (hdl->arm_callback(time_ps)) {
        delete(hdl);
        hdl = NULL;
    }

    FEXIT
    return hdl;
}

gpi_cb_hdl *vpi_impl::register_readwrite_callback(void)
{
    FENTER

    vpi_cb_readwrite *hdl = new vpi_cb_readwrite(vpi_table);

    if (hdl->arm_callback()) {
        delete(hdl);
        hdl = NULL;
    }

    FEXIT
    return hdl;
}

gpi_cb_hdl *vpi_impl::register_value_change_callback(gpi_obj_hdl *gpi_hdl)
{
    FENTER

    vpi_obj_hdl *vpi_obj = reinterpret_cast<vpi_obj_hdl*>(gpi_hdl);
    vpi_cb_value_change *hdl = new vpi_cb_value_change(vpi_table);

    if (hdl->arm_callback(vpi_obj)) {
        delete(hdl);
        hdl = NULL;
    }

    FEXIT
    return hdl;
}

gpi_cb_hdl *vpi_impl::register_readonly_callback(void)
{
    FENTER

    vpi_cb_readonly *hdl = new vpi_cb_readonly(vpi_table);

    if (hdl->arm_callback()) {
        delete(hdl);
        hdl = NULL;
    }

    FEXIT
    return hdl;
}

int vpi_impl::deregister_callback(gpi_cb_hdl *gpi_hdl)
{
    vpi_cb_hdl *vpi_obj = reinterpret_cast<vpi_cb_hdl*>(gpi_hdl);
    return vpi_obj->cleanup_callback();
}

// If the Pything world wants things to shut down then unregister
// the callback for end of sim
void vpi_impl::sim_end(void)
{
    /* Some sims do not seem to be able to deregister the end of sim callback
     * so we need to make sure we have tracked this and not call the handler
     */
    sim_finish_cb->state = VPI_DELETE;
    vpi_control(vpiFinish);
    check_vpi_error();
}

extern "C" {

// Main re-entry point for callbacks from simulator
int32_t handle_vpi_callback(p_cb_data cb_data)
{
    FENTER
    int rv = 0;
    //vpiHandle old_cb;

    vpi_cb_hdl *cb_hdl = (vpi_cb_hdl*)cb_data->user_data;

    if (!cb_hdl)
        LOG_CRITICAL("VPI: Callback data corrupted");

    //cb_hdl->set_state(VPI_PRE_CALL);
    //old_cb = user_data->cb_hdl;
    if (cb_hdl->state == VPI_PRIMED)
        cb_hdl->run_callback();
    //gpi_deregister_callback(cb_hdl);
    
#if 0
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
#endif
    //cb_hdl->set_state(VPI_POST_CALL);

    FEXIT
    return rv;
};


static void register_embed(void)
{
    vpi_table = new vpi_impl("VPI");
    gpi_register_impl(vpi_table);
    gpi_embed_init_python();
}


static void register_initial_callback(void)
{
    sim_init_cb = new vpi_cb_startup(vpi_table);

    /* We ignore the return value here as VCS does some silly
     * things on comilation that means it tries to run through
     * the vlog_startup_routines and so call this routine
     */

    sim_init_cb->arm_callback();
}

static void register_final_callback(void)
{
    sim_finish_cb = new vpi_cb_shutdown(vpi_table);

    /* We ignore the return value here as VCS does some silly
     * things on comilation that means it tries to run through
     * the vlog_startup_routines and so call this routine
     */

    sim_finish_cb->arm_callback();
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

    tfData.user_data    = (char *)&systf_info_level;
    tfData.tfname       = "$info";
    vpi_register_systf( &tfData );

    tfData.user_data    = (char *)&systf_warning_level;
    tfData.tfname       = "$warning";
    vpi_register_systf( &tfData );

    tfData.user_data    = (char *)&systf_error_level;
    tfData.tfname       = "$error";
    vpi_register_systf( &tfData );

    tfData.user_data    = (char *)&systf_fatal_level;
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

}