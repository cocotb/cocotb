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

VpiCbHdl::VpiCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                             vpi_hdl(NULL)
{
    cb_data.reason    = 0;
    cb_data.cb_rtn    = handle_vpi_callback;
    cb_data.obj       = NULL;
    cb_data.time      = NULL;
    cb_data.value     = NULL;
    cb_data.user_data = (char*)this;
}

/* If the user data already has a callback handle then deregister
 * before getting the new one
 */
int VpiCbHdl::arm_callback(void) {
    if (m_state == GPI_PRIMED) {
        fprintf(stderr,
                "Attempt to prime an already primed trigger for %s!\n", 
                m_impl->reason_to_string(cb_data.reason));
    }

    if (vpi_hdl != NULL) {
        fprintf(stderr,
                "We seem to already be registered, deregistering %s!\n",
                m_impl->reason_to_string(cb_data.reason));

        cleanup_callback();
    }

    vpiHandle new_hdl = vpi_register_cb(&cb_data);
    int ret = 0;

    if (!new_hdl) {
        LOG_CRITICAL("VPI: Unable to register a callback handle for VPI type %s(%d)",
                     m_impl->reason_to_string(cb_data.reason), cb_data.reason);
        check_vpi_error();
        ret = -1;
    }

    vpi_hdl = new_hdl;
    m_state = GPI_PRIMED;

    return ret;
}

int VpiCbHdl::cleanup_callback(void)
{
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

const char* VpiSignalObjHdl::get_signal_value_binstr(void)
{
    FENTER
    s_vpi_value value_s = {vpiBinStrVal};
    p_vpi_value value_p = &value_s;

    vpi_get_value(vpi_hdl, value_p);
    check_vpi_error();

    return value_p->value.str;
}

// Value related functions
int VpiSignalObjHdl::set_signal_value(int value)
{
    FENTER
    s_vpi_value value_s;

    value_s.value.integer = value;
    value_s.format = vpiIntVal;

    s_vpi_time vpi_time_s;

    vpi_time_s.type = vpiSimTime;
    vpi_time_s.high = 0;
    vpi_time_s.low  = 0;

    // Use Inertial delay to schedule an event, thus behaving like a verilog testbench
    vpi_put_value(vpi_hdl, &value_s, &vpi_time_s, vpiInertialDelay);
    check_vpi_error();

    FEXIT
    return 0;
}

int VpiSignalObjHdl::set_signal_value(std::string &value)
{
    FENTER
    s_vpi_value value_s;

    std::vector<char> writable(value.begin(), value.end());
    writable.push_back('\0');

    value_s.value.str = &writable[0];
    value_s.format = vpiBinStrVal;

    vpi_put_value(vpi_hdl, &value_s, NULL, vpiNoDelay);
    check_vpi_error();

    FEXIT
    return 0;
}

GpiCbHdl * VpiSignalObjHdl::value_change_cb(void)
{
    value_cb = new VpiValueCbHdl(VpiObjHdl::m_impl, this);

    if (value_cb->arm_callback())
        return NULL;

    return value_cb;
}

VpiValueCbHdl::VpiValueCbHdl(GpiImplInterface *impl, VpiSignalObjHdl *sig) : VpiCbHdl(impl)
{
    vpi_time.type = vpiSuppressTime;

    cb_data.reason = cbValueChange;
    cb_data.time = &vpi_time;
    cb_data.obj = sig->get_handle();
}

int VpiValueCbHdl::cleanup_callback(void)
{
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

    return rc;
}

VpiStartupCbHdl::VpiStartupCbHdl(GpiImplInterface *impl) : VpiCbHdl(impl)
{
    cb_data.reason = cbStartOfSimulation;
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

VpiShutdownCbHdl::VpiShutdownCbHdl(GpiImplInterface *impl) : VpiCbHdl(impl)
{
    cb_data.reason = cbEndOfSimulation;
}

int VpiShutdownCbHdl::run_callback(void) {
    LOG_WARN("Shutdown called");
    gpi_embed_end();
    return 0;
}

VpiTimedCbHdl::VpiTimedCbHdl(GpiImplInterface *impl, uint64_t time_ps) : VpiCbHdl(impl)
{
    vpi_time.type = vpiSimTime;
    vpi_time.high = (uint32_t)(time_ps>>32);
    vpi_time.low  = (uint32_t)(time_ps);

    cb_data.reason = cbAfterDelay;
    cb_data.time = &vpi_time;
}

VpiReadwriteCbHdl::VpiReadwriteCbHdl(GpiImplInterface *impl) : VpiCbHdl(impl)
{
    vpi_time.type = vpiSimTime;
    vpi_time.high = 0;
    vpi_time.low = 0;

    cb_data.reason = cbReadWriteSynch;
    cb_data.time = &vpi_time;
}

VpiReadOnlyCbHdl::VpiReadOnlyCbHdl(GpiImplInterface *impl) : VpiCbHdl(impl)
{
    vpi_time.type = vpiSimTime;
    vpi_time.high = 0;
    vpi_time.low = 0;

    cb_data.reason = cbReadOnlySynch;
    cb_data.time = &vpi_time;
}

VpiNextPhaseCbHdl::VpiNextPhaseCbHdl(GpiImplInterface *impl) : VpiCbHdl(impl)
{
    vpi_time.type = vpiSimTime;
    vpi_time.high = 0;
    vpi_time.low = 0;

    cb_data.reason = cbNextSimTime;
    cb_data.time = &vpi_time;
}