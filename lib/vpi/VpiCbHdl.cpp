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

#include "VpiImpl.h"
#include <vector>

extern "C" int32_t handle_vpi_callback(p_cb_data cb_data);

vpiHandle VpiObjHdl::get_handle(void)
{
    return vpi_hdl;
}

/**
 * @brief   Get a handle to an object under the scope of parent
 *
 * @param   name of the object to find, below this object in the hierachy
 *
 * @return  gpi_sim_hdl for the new object or NULL if object not found
 */
GpiObjHdl *VpiObjHdl::get_handle_by_name(std::string &name)
{
    FENTER
    GpiObjHdl *rv = NULL;
    vpiHandle obj;
    vpiHandle iterator;
    std::vector<char> writable(name.begin(), name.end());
    writable.push_back('\0');
    //int len;
    //char *buff;

    // Structures aren't technically a scope, according to the LRM. If parent
    // is a structure then we have to iterate over the members comparing names
    if (vpiStructVar == vpi_get(vpiType, vpi_hdl)) {

        iterator = vpi_iterate(vpiMember, vpi_hdl);

        for (obj = vpi_scan(iterator); obj != NULL; obj = vpi_scan(iterator)) {

            if (!strcmp(name.c_str(), strrchr(vpi_get_str(vpiName, obj), 46) + 1))
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

    #if 0
     Do we need this
    if (name)
        len = strlen(name) + 1;

    buff = (char *)malloc(len);
    if (buff == NULL) {
        LOG_CRITICAL("VPI: Attempting allocate string buffer failed!");
        return NULL;
    }

    strncpy(buff, name, len);
    #endif
    

    obj = vpi_handle_by_name(&writable[0], vpi_hdl);
    if (!obj) {
        LOG_DEBUG("VPI: Handle '%s' not found!", name.c_str());

        // NB we deliberately don't dump an error message here because it's
        // a valid use case to attempt to grab a signal by name - for example
        // optional signals on a bus.
        // check_vpi_error();
        //free(buff);
        return NULL;
    }

    //free(buff);

success:
    //  rv = new VpiObjHdl(obj);

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
GpiObjHdl *VpiObjHdl::get_handle_by_index(uint32_t index)
{
    FENTER
    vpiHandle obj;
    GpiObjHdl *rv = NULL;

    obj = vpi_handle_by_index(vpi_hdl, index);
    if (!obj) {
        LOG_ERROR("VPI: Handle idx '%d' not found!", index);
        return NULL;
    }

    //rv = new VpiObjHdl(obj, this);

    FEXIT
    return rv;
}

/* If the user data already has a callback handle then deregister
 * before getting the new one
 */
int VpiCbHdl::register_cb(p_cb_data cb_data) {
    if (m_state == GPI_PRIMED) {
        fprintf(stderr,
                "Attempt to prime an already primed trigger for %s!\n", 
                m_impl->reason_to_string(cb_data->reason));
    }

    if (vpi_hdl != NULL) {
        fprintf(stderr,
                "We seem to already be registered, deregistering %s!\n",
                m_impl->reason_to_string(cb_data->reason));

        cleanup_callback();
    }

    vpiHandle new_hdl = vpi_register_cb(cb_data);
    int ret = 0;

    if (!new_hdl) {
        LOG_CRITICAL("VPI: Unable to register callback a handle for VPI type %s(%d)",
                     m_impl->reason_to_string(cb_data->reason), cb_data->reason);
        check_vpi_error();
        ret = -1;
    }

    vpi_hdl = new_hdl;
    m_state = GPI_PRIMED;

    return ret;
}

int VpiCbHdl::cleanup_callback(void)
{
    return 0;
}

int VpiCbHdl::arm_callback(void)
{
    return 0;
}

int VpiStartupCbHdl::run_callback(void) {
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

int VpiStartupCbHdl::arm_callback(void) {
    s_cb_data cb_data_s;

    cb_data_s.reason    = cbStartOfSimulation;
    cb_data_s.cb_rtn    = handle_vpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = NULL;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char*)this;

    return register_cb(&cb_data_s);
}

int VpiShutdownCbHdl::run_callback(void) {
    LOG_WARN("Shutdown called");
    gpi_embed_end();
    return 0;
}

int VpiShutdownCbHdl::arm_callback(void) {
    s_cb_data cb_data_s;

    cb_data_s.reason    = cbEndOfSimulation;
    cb_data_s.cb_rtn    = handle_vpi_callback;
    cb_data_s.obj       = NULL;
    cb_data_s.time      = NULL;
    cb_data_s.value     = NULL;
    cb_data_s.user_data = (char*)this;

    return register_cb(&cb_data_s);
}


int VpiTimedCbHdl::arm_callback(uint64_t time_ps) {
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


#if 0
class vpi_onetime_cb : public vpi_cb_hdl {
public:
    vpi_onetime_cb(gpi_m_impl_interface *m_impl) : vpi_cb_hdl(m_impl) { }
    int cleanup_callback(void) {
        FENTER
        //LOG_WARN("Cleanup %p state is %d", this, state);
        int rc;
        if (!vpi_hdl) {
            LOG_CRITICAL("VPI: passed a NULL pointer : ABORTING");
            exit(1);
        }

        // If the callback has not been called we also need to call
        // remove as well
        if (m_state == GPI_PRIMED) {

            rc = vpi_remove_cb(vpi_hdl);
            if (!rc) {
                check_vpi_error();
                return rc;
            }
        }

        vpi_hdl = NULL;
        m_state = GPI_FREE;
        return rc;
    }
    virtual ~vpi_onetime_cb() { }
};

class vpi_recurring_cb : public vpi_cb_hdl {
public:
    vpi_recurring_cb(gpi_m_impl_interface *m_impl) : vpi_cb_hdl(m_impl) { }
    int cleanup_callback(void) {
        FENTER
        //LOG_WARN("Cleanup %p", this);
        int rc;
        if (!vpi_hdl) {
            LOG_CRITICAL("VPI: passed a NULL pointer : ABORTING");
            exit(1);
        }

        rc = vpi_remove_cb(vpi_hdl);
        check_vpi_error();

        vpi_hdl = NULL;
        m_state = GPI_FREE;

        FEXIT
        return rc;
    }
    virtual ~vpi_recurring_cb() { }
};

class vpi_cb_value_change : public vpi_recurring_cb {
private:
    s_vpi_value cb_value;
public:
    vpi_cb_value_change(gpi_m_impl_interface *m_impl) : vpi_recurring_cb(m_impl) {
        cb_value.format = vpiIntVal;
    }
    int arm_callback(vpi_obj_hdl *vpi_hdl) {
        s_cb_data cb_data_s;
        s_vpi_time vpi_time_s = {.type = vpiSuppressTime };

        cb_data_s.reason    = cbValueChange;
        cb_data_s.cb_rtn    = handle_vpi_callback;
        cb_data_s.obj       = vpi_hdl->vpi_hdl;
        cb_data_s.time      = &vpi_time_s;
        cb_data_s.value     = &cb_value;
        cb_data_s.user_data = (char *)this;

        return register_cb(&cb_data_s);
    }
    virtual ~vpi_cb_value_change() { }
};

class vpi_cb_readonly : public vpi_onetime_cb {
public:
    vpi_cb_readonly(gpi_m_impl_interface *m_impl) : vpi_onetime_cb(m_impl) { }
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

    virtual ~vpi_cb_readonly() { }
};


class vpi_cb_timed : public vpi_onetime_cb {
public:
    vpi_cb_timed(gpi_m_impl_interface *m_impl) : vpi_onetime_cb(m_impl) { }

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

    virtual ~vpi_cb_timed() { }
};

class vpi_cb_readwrite : public vpi_onetime_cb {
public:
    vpi_cb_readwrite(gpi_m_impl_interface *m_impl) : vpi_onetime_cb(m_impl) { }

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

    virtual ~vpi_cb_readwrite() { }
};

class vpi_cb_nexttime : public vpi_onetime_cb {
public:
    vpi_cb_nexttime(gpi_m_impl_interface *m_impl) : vpi_onetime_cb(m_impl) { }

    int arm_callback(void) {
        s_cb_data cb_data_s;
        s_vpi_time vpi_time_s;

        vpi_time_s.type = vpiSimTime;
        vpi_time_s.high = 0;
        vpi_time_s.low = 0;

        cb_data_s.reason    = cbNextSimTime;
        cb_data_s.cb_rtn    = handle_vpi_callback;
        cb_data_s.obj       = NULL;
        cb_data_s.time      = &vpi_time_s;
        cb_data_s.value     = NULL;
        cb_data_s.user_data = (char *)this;

        return register_cb(&cb_data_s);
    }

    virtual ~vpi_cb_nexttime() { }
};

#endif