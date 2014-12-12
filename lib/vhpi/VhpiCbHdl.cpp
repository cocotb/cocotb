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

VhpiSignalObjHdl::~VhpiSignalObjHdl()
{
    if (m_value.format == vhpiEnumVecVal ||
        m_value.format == vhpiLogicVecVal) {
        free(m_value.value.enumvs);
    }

    free(m_binvalue.value.str);
}

int VhpiSignalObjHdl::initialise(std::string &name) {
    // Determine the type of object, either scalar or vector
    m_value.format = vhpiObjTypeVal;
    m_value.bufSize = 0;
    m_value.value.str = NULL;

    vhpi_get_value(GpiObjHdl::get_handle<vhpiHandleT>(), &m_value);
    check_vhpi_error();

    switch (m_value.format) {
        case vhpiEnumVal:
        case vhpiLogicVal: {
            m_value.value.enumv = vhpi0;
            break;
        }

        case vhpiEnumVecVal:
        case vhpiLogicVecVal: {
            m_size = vhpi_get(vhpiSizeP, GpiObjHdl::get_handle<vhpiHandleT>());
            m_value.bufSize = m_size*sizeof(vhpiEnumT); 
            m_value.value.enumvs = (vhpiEnumT *)malloc(m_value.bufSize);
            if (!m_value.value.enumvs) {
                LOG_CRITICAL("Unable to alloc mem for write buffer");
            }

            break;
        }

        default: {
            LOG_CRITICAL("Unable to determine property for %s (%d) format object",
                         ((VhpiImpl*)GpiObjHdl::m_impl)->format_to_string(m_value.format), m_value.format);
        }
    }

    /* We also alloc a second value member for use with read string operations */
    m_binvalue.format = vhpiBinStrVal;
    m_binvalue.bufSize = 0;
    m_binvalue.value.str = NULL;

    int new_size = vhpi_get_value(GpiObjHdl::get_handle<vhpiHandleT>(), &m_binvalue);

    m_binvalue.bufSize = new_size*sizeof(vhpiCharT) + 1;
    m_binvalue.value.str = (vhpiCharT *)calloc(m_binvalue.bufSize, m_binvalue.bufSize);

    if (!m_value.value.str) {
        LOG_CRITICAL("Unable to alloc mem for read buffer");
    }

    GpiObjHdl::initialise(name);

    return 0;
}

VhpiCbHdl::VhpiCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl)
{
    cb_data.reason    = 0;
    cb_data.cb_rtn    = handle_vhpi_callback;
    cb_data.obj       = NULL;
    cb_data.time      = NULL;
    cb_data.value     = NULL;
    cb_data.user_data = (char *)this;

    vhpi_time.high = 0;
    vhpi_time.low = 0;
}

int VhpiCbHdl::cleanup_callback(void)
{
    /* For non timer callbacks we disable rather than remove */
    int ret = 0;
    if (m_state == GPI_FREE)
        return 0;

    vhpiStateT cbState = (vhpiStateT)vhpi_get(vhpiStateP, get_handle<vhpiHandleT>());
    if (vhpiEnable == cbState) {
        ret = vhpi_disable_cb(get_handle<vhpiHandleT>());
        m_state = GPI_FREE;
    }

    if (ret)
        check_vhpi_error();

    return 0;
}

int VhpiCbHdl::arm_callback(void)
{
    int ret = 0;
    vhpiStateT cbState;

    if (m_state == GPI_PRIMED)
        return 0;

    /* Do we already have a handle, if so and it is disabled then
       just re-enable it */

    if (get_handle<vhpiHandleT>()) {
        cbState = (vhpiStateT)vhpi_get(vhpiStateP, get_handle<vhpiHandleT>());
        if (vhpiDisable == cbState) {
            if (vhpi_enable_cb(get_handle<vhpiHandleT>())) {
                check_vhpi_error();
                ret = -1;
            }
         }
    } else {

        vhpiHandleT new_hdl = vhpi_register_cb(&cb_data, vhpiReturnCb);

        if (!new_hdl) {
            LOG_CRITICAL("VHPI: Unable to register callback a handle for VHPI type %s(%d)",
                         m_impl->reason_to_string(cb_data.reason), cb_data.reason);
            check_vhpi_error();
            ret = -1;
        }

        cbState = (vhpiStateT)vhpi_get(vhpiStateP, new_hdl);
        if (vhpiEnable != cbState) {
            LOG_CRITICAL("VHPI ERROR: Registered callback isn't enabled! Got %d\n", cbState);
        }

        m_obj_hdl = new_hdl;
    }
    m_state = GPI_PRIMED;

    return ret;
}

// Value related functions
const vhpiEnumT VhpiSignalObjHdl::chr2vhpi(const char value)
{
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

// Value related functions
int VhpiSignalObjHdl::set_signal_value(int value)
{
    switch (m_value.format) {
        case vhpiEnumVal:
        case vhpiLogicVal: {
            m_value.value.enumv = value ? vhpi1 : vhpi0;
            break;
        }

        case vhpiEnumVecVal:
        case vhpiLogicVecVal: {
            unsigned int i;
            for (i=0; i<m_size; i++)
                m_value.value.enumvs[m_size-i-1] = value&(1<<i) ? vhpi1 : vhpi0;

            break;
        }

        default: {
            LOG_CRITICAL("VHPI type of object has changed at runtime, big fail");
        }
    }
    vhpi_put_value(GpiObjHdl::get_handle<vhpiHandleT>(), &m_value, vhpiForcePropagate);
    check_vhpi_error();
    return 0;
}

int VhpiSignalObjHdl::set_signal_value(std::string &value)
{
    switch (m_value.format) {
        case vhpiEnumVal:
        case vhpiLogicVal: {
            m_value.value.enumv = chr2vhpi(value.c_str()[0]);
            break;
        }

        case vhpiEnumVecVal:
        case vhpiLogicVecVal: {

            unsigned int len = value.length();

            if (len > m_size)  {
                LOG_ERROR("VHPI: Attempt to write string longer than signal %d > %d",
                          len, m_size);
                return -1;
            }

            std::string::iterator iter;

            unsigned int i = 0;
            for (iter = value.begin();
                 iter != value.end();
                 iter++, i++) {
                m_value.value.enumvs[i] = chr2vhpi(*iter);
            }

            // Fill bits at the end of the value to 0's
            for (i = len; i < m_size; i++) {
                m_value.value.enumvs[i] = vhpi0;
            }

            break;
        }

        default: {
           LOG_CRITICAL("VHPI type of object has changed at runtime, big fail");
        }
    }

    vhpi_put_value(GpiObjHdl::get_handle<vhpiHandleT>(), &m_value, vhpiForcePropagate);
    check_vhpi_error();
    return 0;
}

const char* VhpiSignalObjHdl::get_signal_value_binstr(void)
{
    vhpi_get_value(GpiObjHdl::get_handle<vhpiHandleT>(), &m_binvalue);
    check_vhpi_error();

    return m_binvalue.value.str;
}

GpiCbHdl * VhpiSignalObjHdl::value_change_cb(unsigned int edge)
{
    VhpiValueCbHdl *cb = NULL;

    switch (edge) {
    case 1:
        cb = &m_rising_cb;
        break;
    case 2:
        cb = &m_falling_cb;
        break;
    case 3:
        cb = &m_either_cb;
        break;
    default:
        return NULL;
    }

    if (cb->arm_callback()) {
        return NULL;
    }

    return cb;
}

VhpiValueCbHdl::VhpiValueCbHdl(GpiImplInterface *impl,
                               VhpiSignalObjHdl *sig,
                               int edge) : GpiCbHdl(impl),
                                           VhpiCbHdl(impl),
                                           GpiValueCbHdl(impl,sig,edge)
{
    cb_data.reason = vhpiCbValueChange;
    cb_data.time = &vhpi_time;
    cb_data.obj = m_signal->get_handle<vhpiHandleT>();
}

VhpiStartupCbHdl::VhpiStartupCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                                             VhpiCbHdl(impl)
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

VhpiShutdownCbHdl::VhpiShutdownCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                                               VhpiCbHdl(impl)
{
    cb_data.reason = vhpiCbEndOfSimulation;
}

int VhpiShutdownCbHdl::run_callback(void) {
    set_call_state(GPI_DELETE);
    gpi_embed_end();
    return 0;
}

VhpiTimedCbHdl::VhpiTimedCbHdl(GpiImplInterface *impl, uint64_t time_ps) : GpiCbHdl(impl),
                                                                           VhpiCbHdl(impl)
{
    vhpi_time.high = (uint32_t)(time_ps>>32);
    vhpi_time.low  = (uint32_t)(time_ps); 

    cb_data.reason = vhpiCbAfterDelay;
    cb_data.time = &vhpi_time;
}

int VhpiTimedCbHdl::cleanup_callback(void)
{
    if (m_state == GPI_FREE)
        return 1;

    vhpi_remove_cb(get_handle<vhpiHandleT>());

    m_obj_hdl = NULL;
    m_state = GPI_FREE;
    return 1;
}

VhpiReadwriteCbHdl::VhpiReadwriteCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                                                 VhpiCbHdl(impl)
{
    cb_data.reason = vhpiCbRepEndOfProcesses;
    cb_data.time = &vhpi_time;
}

VhpiReadOnlyCbHdl::VhpiReadOnlyCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                                               VhpiCbHdl(impl)
{
    cb_data.reason = vhpiCbRepLastKnownDeltaCycle;
    cb_data.time = &vhpi_time;
}

VhpiNextPhaseCbHdl::VhpiNextPhaseCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                                                 VhpiCbHdl(impl)
{
    cb_data.reason = vhpiCbRepNextTimeStep;
    cb_data.time = &vhpi_time;
}
