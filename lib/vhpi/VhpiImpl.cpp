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


#include "VhpiImpl.h"
#include <vector>

extern "C" {

static VhpiCbHdl *sim_init_cb;
static VhpiCbHdl *sim_finish_cb;
static VhpiImpl  *vhpi_table;

}

const char * vhpi_format_to_string(int reason)
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

// Value related functions
const vhpiEnumT chr2vhpi(const char value)
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

#if 0
class VhpiObjHdl : public GpiObjHdl {
private:
    int m_size;
    vhpiValueT m_value;
public:
    VhpiObjHdl(vhpiHandleT hdl, gpi_impl_interface *impl) : GpiObjHdl(impl),
                                                              m_size(0),
                                                              vhpi_hdl(hdl) { }
    virtual ~VhpiObjHdl() {
        if (m_value.format == vhpiEnumVecVal ||
            m_value.format == vhpiLogicVecVal) {
            free(m_value.value.enumvs);
        }
    }
public:
    vhpiHandleT vhpi_hdl;

    int initialise(void) {
        // Determine the type of object, either scalar or vector
        m_value.format = vhpiObjTypeVal;
        m_value.bufSize = 0;
        m_value.value.str = NULL;

        vhpi_get_value(vhpi_hdl, &m_value);
        check_vhpi_error();

        switch (m_value.format) {
            case vhpiEnumVal:
            case vhpiLogicVal: {
                m_value.value.enumv = vhpi0;
                break;
            }

            case vhpiEnumVecVal:
            case vhpiLogicVecVal: {
                m_size = vhpi_get(vhpiSizeP, vhpi_hdl);
                m_value.bufSize = m_size*sizeof(vhpiEnumT); 
                m_value.value.enumvs = (vhpiEnumT *)malloc(m_size*sizeof(vhpiEnumT));

                memset(&m_value.value.enumvs, m_size, vhpi0);
                //for (i=0; i<size; i++)
                //    value_s.value.enumvs[size-i-1] = value&(1<<i) ? vhpi1 : vhpi0;

                break;
            }

            default: {
                LOG_CRITICAL("Unable to assign value to %s (%d) format object",
                             vhpi_format_to_string(m_value.format), m_value.format);
            }
        }
        return 0;
    }

    int write_new_value(int value) {
        switch (m_value.format) {
            case vhpiEnumVal:
            case vhpiLogicVal: {
                m_value.value.enumv = value ? vhpi1 : vhpi0;
                break;
            }

            case vhpiEnumVecVal:
            case vhpiLogicVecVal: {
                int i;
                for (i=0; i<m_size; i++)
                    m_value.value.enumvs[m_size-i-1] = value&(1<<i) ? vhpi1 : vhpi0;

                break;
            }

            default: {
                LOG_CRITICAL("VHPI type of object has changed at runtime, big fail");
            }
        }
        vhpi_put_value(vhpi_hdl, &m_value, vhpiForcePropagate);
        return check_vhpi_error();
    }

    int write_new_value(const char *str) {
        switch (m_value.format) {
            case vhpiEnumVal:
            case vhpiLogicVal: {
                m_value.value.enumv = chr2vhpi(*str);
                break;
            }

            case vhpiEnumVecVal:
            case vhpiLogicVecVal: {

                const char *ptr;
                int len = strlen(str);
                if (len > m_size) {
                    LOG_ERROR("VHPI: Attempt to write string longer than signal %d > %d",
                              len, m_size);
                    return -1;
                }
                int i;
                for (i=0, ptr=str; i<len; ptr++, i++)
                    m_value.value.enumvs[i] = chr2vhpi(*ptr);

                // Initialise to 0s
                for (i=len; i<m_size; i++)
                    m_value.value.enumvs[i] = vhpi0;

                break;
            }

            default: {
                LOG_CRITICAL("Unable to assign value to %s (%d) format object",
                             vhpi_format_to_string(m_value.format), m_value.format);
            }
        }

        vhpi_put_value(vhpi_hdl, &m_value, vhpiForcePropagate);
        return check_vhpi_error();
    }
};
#endif

const char *VhpiImpl::reason_to_string(int reason) 
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

void VhpiImpl::get_sim_time(uint32_t *high, uint32_t *low)
{
    vhpiTimeT vhpi_time_s;
    vhpi_get_time(&vhpi_time_s, NULL);
    check_vhpi_error();
    *high = vhpi_time_s.high;
    *low = vhpi_time_s.low;
}

GpiObjHdl *VhpiImpl::get_root_handle(const char* name)
{
    FENTER
    vhpiHandleT root;
    vhpiHandleT dut;
    GpiObjHdl *rv;

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

    rv = new VhpiObjHdl(this, root);

    FEXIT
    return rv;
}


GpiCbHdl *VhpiImpl::register_timed_callback(uint64_t time_ps)
{
    VhpiTimedCbHdl *hdl = new VhpiTimedCbHdl(this, time_ps);

    if (hdl->arm_callback()) {
        delete(hdl);
        hdl = NULL;
    }

    return hdl;
}

void VhpiImpl::sim_end(void)
{
    sim_finish_cb = NULL;
    vhpi_control(vhpiFinish);
    check_vhpi_error();
}

extern "C" {

// Main entry point for callbacks from simulator
void handle_vhpi_callback(const vhpiCbDataT *cb_data)
{
    FENTER

    VhpiCbHdl *cb_hdl = (VhpiCbHdl*)cb_data->user_data;

    if (!cb_hdl)
        LOG_CRITICAL("VPI: Callback data corrupted");

    LOG_DEBUG("Running %p", cb_hdl);

    if (cb_hdl->get_call_state() == GPI_PRIMED) {
        cb_hdl->set_call_state(GPI_PRE_CALL);
        cb_hdl->run_callback();
        cb_hdl->set_call_state(GPI_POST_CALL);
    }

    gpi_deregister_callback(cb_hdl);

    FEXIT
    return;
};

static void register_initial_callback(void)
{
    FENTER
    sim_init_cb = new VhpiStartupCbHdl(vhpi_table);
    sim_init_cb->arm_callback();
    FEXIT
}

static void register_final_callback(void)
{
    FENTER
    sim_finish_cb = new VhpiShutdownCbHdl(vhpi_table);
    sim_finish_cb->arm_callback();
    FEXIT
}

static void register_embed(void)
{
    vhpi_table = new VhpiImpl("VHPI");
    gpi_register_impl(vhpi_table);
    gpi_embed_init_python();
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

}