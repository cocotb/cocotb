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

#include "VhpiImpl.h"
#include <vector>

extern "C" {
static VhpiCbHdl *sim_init_cb;
static VhpiCbHdl *sim_finish_cb;
static VhpiImpl  *vhpi_table;
}

const char * VhpiImpl::format_to_string(int format)
{
    switch (format) {
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

GpiObjHdl *VhpiImpl::create_gpi_obj_from_handle(vhpiHandleT new_hdl, std::string &name)
{
    vhpiIntT type;
    GpiObjHdl *new_obj = NULL;

    if (vhpiVerilog == (type = vhpi_get(vhpiKindP, new_hdl))) {
        LOG_DEBUG("vhpiVerilog returned from vhpi_get(vhpiType, ...)")
        return NULL;
    }
    /* What sort of isntance is this ?*/
    switch (type) {
        case vhpiPortDeclK:
        case vhpiSigDeclK:
        case vhpiIndexedNameK:
            new_obj = new VhpiSignalObjHdl(this, new_hdl);
            break;
        case vhpiCompInstStmtK:
            new_obj = new GpiObjHdl(this, new_hdl);
            break;
        default:
            LOG_WARN("Not able to map type %d to object.");
            return NULL;
    }

    new_obj->initialise(name);

    return new_obj;
}

GpiObjHdl *VhpiImpl::native_check_create(std::string &name, GpiObjHdl *parent)
{
    vhpiHandleT new_hdl;
    std::vector<char> writable(name.begin(), name.end());
    writable.push_back('\0');

    new_hdl = vhpi_handle_by_name(&writable[0], NULL);

    if (new_hdl == NULL) {
        LOG_DEBUG("Unable to query vhpi_handle_by_name %s", name.c_str());
        return NULL;
    }

    GpiObjHdl* new_obj = create_gpi_obj_from_handle(new_hdl, name);
    if (new_obj == NULL) {
        vhpi_release_handle(new_hdl);
        LOG_DEBUG("Unable to fetch object %s", name.c_str());
        return NULL;
    }

    return new_obj;
}

GpiObjHdl *VhpiImpl::native_check_create(uint32_t index, GpiObjHdl *parent)
{
    GpiObjHdl *parent_hdl = sim_to_hdl<GpiObjHdl*>(parent);
    vhpiHandleT vpi_hdl = parent_hdl->get_handle<vhpiHandleT>();
    vhpiHandleT new_hdl;

    new_hdl = vhpi_handle_by_index(vhpiIndexedNames, vpi_hdl, index);

    if (new_hdl == NULL) {
        LOG_DEBUG("Unable to query vhpi_handle_by_index %s", index);
        return NULL;
    }

    std::string name = vhpi_get_str(vhpiNameP, new_hdl);
    GpiObjHdl* new_obj = create_gpi_obj_from_handle(new_hdl, name);
    if (new_obj == NULL) {
        vhpi_release_handle(new_hdl);
        LOG_DEBUG("Could not fetch object below entity (%s) at index (%d)",
                                 parent->get_name_str(), index);
        return NULL;
    }

    return new_obj;
}

GpiObjHdl *VhpiImpl::get_root_handle(const char* name)
{
    FENTER
    vhpiHandleT root;
    vhpiHandleT dut;
    GpiObjHdl *rv;
    std::string root_name = name;

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

    rv = new GpiObjHdl(this, root);
    rv->initialise(root_name);

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

GpiCbHdl *VhpiImpl::register_readwrite_callback(void)
{
    if (m_read_write.arm_callback())
        return NULL;

    return &m_read_write;
}

GpiCbHdl *VhpiImpl::register_readonly_callback(void)
{
    if (m_read_only.arm_callback())
        return NULL;

    return &m_read_only;
}

GpiCbHdl *VhpiImpl::register_nexttime_callback(void)
{
    if (m_next_phase.arm_callback())
        return NULL;

    return &m_next_phase;
}

int VhpiImpl::deregister_callback(GpiCbHdl *gpi_hdl)
{
    gpi_hdl->cleanup_callback();
    return 0;
}

void VhpiImpl::sim_end(void)
{
    sim_finish_cb->set_call_state(GPI_DELETE);
    vhpi_control(vhpiFinish);
    check_vhpi_error();
}

extern "C" {

// Main entry point for callbacks from simulator
void handle_vhpi_callback(const vhpiCbDataT *cb_data)
{
    VhpiCbHdl *cb_hdl = (VhpiCbHdl*)cb_data->user_data;

    if (!cb_hdl)
        LOG_CRITICAL("VHPI: Callback data corrupted");

    gpi_cb_state_e old_state = cb_hdl->get_call_state();

    if (old_state == GPI_PRIMED) { 

        cb_hdl->set_call_state(GPI_CALL);
        cb_hdl->run_callback();

        gpi_cb_state_e new_state = cb_hdl->get_call_state();
        
        /* We have re-primed in the handler */
        if (new_state != GPI_PRIMED)
            if (cb_hdl->cleanup_callback()) {
                delete cb_hdl;
            }

    }

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
    gpi_load_extra_libs();
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

GPI_ENTRY_POINT(vhpi, register_embed)
