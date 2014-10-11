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
*    * Neither the name of Potential Ventures Ltd,
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

#include "VhpiImpl.h"
#include <vector>

extern "C" void handle_vhpi_callback(const vhpiCbDataT *cb_data);

vhpiHandleT VhpiObjHdl::get_handle(void)
{
    return vhpi_hdl;
}

VhpiCbHdl::VhpiCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                               vhpi_hdl(NULL)
{
    cb_data.reason    = 0;
    cb_data.cb_rtn    = handle_vhpi_callback;
    cb_data.obj       = NULL;
    cb_data.time      = NULL;
    cb_data.value     = NULL;
    cb_data.user_data = (char *)this;
}

int VhpiCbHdl::cleanup_callback(void)
{
    vhpiStateT cbState = (vhpiStateT)vhpi_get(vhpiStateP, vhpi_hdl);
    if (vhpiMature == cbState)
        return vhpi_remove_cb(vhpi_hdl);
    return 0;
}

int VhpiCbHdl::arm_callback(void)
{
    vhpiHandleT new_hdl = vhpi_register_cb(&cb_data, vhpiReturnCb);
    int ret = 0;

    if (!new_hdl) {
        LOG_CRITICAL("VHPI: Unable to register callback a handle for VHPI type %s(%d)",
                     m_impl->reason_to_string(cb_data.reason), cb_data.reason);
        check_vhpi_error();
        ret = -1;
    }

    vhpiStateT cbState = (vhpiStateT)vhpi_get(vhpiStateP, new_hdl);
    if (cbState != vhpiEnable) {
        LOG_CRITICAL("VHPI ERROR: Registered callback isn't enabled! Got %d\n", cbState);
    }

    vhpi_hdl = new_hdl;
    m_state = GPI_PRIMED;

    return ret;
}

const char* VhpiSignalObjHdl::get_signal_value_binstr(void)
{
    s_vpi_value value_s = {vpiBinStrVal};

    vpi_get_value(vhpi_hdl, &value_s);
    check_vhpi_error();

    LOG_WARN("Value back was %s", value_s.value.str);

    return value_s.value.str;
}

// Value related functions
int VhpiSignalObjHdl::set_signal_value(int value)
{
 
    return 0;
}

int VhpiSignalObjHdl::set_signal_value(std::string &value)
{
 
    return 0;
}

VhpiStartupCbHdl::VhpiStartupCbHdl(GpiImplInterface *impl) : VhpiCbHdl(impl)
{
    cb_data.reason = vhpiCbStartOfSimulation;
}

int VhpiStartupCbHdl::run_callback(void) {
    gpi_sim_info_t sim_info;
    sim_info.argc = 0;
    sim_info.argv = NULL;
    sim_info.product = gpi_copy_name(vhpi_get_str(vhpiNameP, NULL));
    sim_info.version = gpi_copy_name(vhpi_get_str(vhpiToolVersionP, NULL));
    gpi_embed_init(&sim_info);

    free(sim_info.product);
    free(sim_info.version);

    return 0;
}

VhpiShutdownCbHdl::VhpiShutdownCbHdl(GpiImplInterface *impl) : VhpiCbHdl(impl)
{
    cb_data.reason = vhpiCbEndOfSimulation;
}

int VhpiShutdownCbHdl::run_callback(void) {
    LOG_WARN("Shutdown called");
    gpi_embed_end();
    return 0;
}

VhpiTimedCbHdl::VhpiTimedCbHdl(GpiImplInterface *impl, uint64_t time_ps) : VhpiCbHdl(impl)
{
    vhpi_time.high = (uint32_t)(time_ps>>32);
    vhpi_time.low  = (uint32_t)(time_ps); 

    cb_data.reason = vhpiCbAfterDelay;
    cb_data.time = &vhpi_time;
}