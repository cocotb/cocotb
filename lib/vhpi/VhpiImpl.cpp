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
#include <algorithm>

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
    case vhpiRawDataVal:
        return "vhpiRawDataVal";

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

// Determine whether a VHPI object type is a constant or not
bool is_const(vhpiIntT vhpitype)
{
    switch (vhpitype) {
        case vhpiConstDeclK:
        case vhpiGenericDeclK:
            return true;
        default:
            return false;
    }
}

gpi_objtype_t to_gpi_objtype(vhpiIntT vhpitype)
{
    switch (vhpitype) {
        case vhpiPortDeclK:
        case vhpiSigDeclK:
        case vhpiIndexedNameK:
        case vhpiSelectedNameK:
        case vhpiVarDeclK:
        case vhpiVarParamDeclK:
        case vhpiSliceNameK:
            return GPI_REGISTER;

        case vhpiArrayTypeDeclK:
            return GPI_ARRAY;

        case vhpiEnumLiteralK:
        case vhpiEnumTypeDeclK:
            return GPI_ENUM;

        case vhpiConstDeclK:
        case vhpiGenericDeclK:
            return GPI_PARAMETER;

        case vhpiRecordTypeDeclK:
            return GPI_STRUCTURE;

        case vhpiForGenerateK:
        case vhpiIfGenerateK:
        case vhpiCompInstStmtK:
        case vhpiEntityDeclK:
        case vhpiRootInstK:
        case vhpiProcessStmtK:
        case vhpiSimpleSigAssignStmtK:
        case vhpiCondSigAssignStmtK:
        case vhpiSelectSigAssignStmtK:
            return GPI_MODULE;

        default:
            LOG_DEBUG("Unable to map VHPI type %d onto GPI type", vhpitype);
            return GPI_UNKNOWN;
    }
}



GpiObjHdl *VhpiImpl::create_gpi_obj_from_handle(vhpiHandleT new_hdl,
                                                std::string &name,
                                                std::string &fq_name)
{
    vhpiIntT type;
    gpi_objtype_t gpi_type;
    GpiObjHdl *new_obj = NULL;
    bool modifiable;
    bool logic;

    if (vhpiVerilog == (type = vhpi_get(vhpiKindP, new_hdl))) {
        LOG_DEBUG("vhpiVerilog returned from vhpi_get(vhpiType, ...)")
        return NULL;
    }

    /* We need to delve further here to detemine how to later set
       the values of an object */
    vhpiHandleT query_hdl;
    vhpiHandleT base_hdl = vhpi_handle(vhpiBaseType, new_hdl);

    query_hdl = base_hdl ? base_hdl : new_hdl;

    vhpiIntT base_type = vhpi_get(vhpiKindP, query_hdl);
    vhpiIntT is_static = vhpi_get(vhpiStaticnessP, query_hdl);

    gpi_type = to_gpi_objtype(base_type);
    LOG_DEBUG("Creating %s of type %d (%s)",
              vhpi_get_str(vhpiFullNameP, new_hdl),
              gpi_type,
              vhpi_get_str(vhpiKindStrP, query_hdl));

    /* Non locally static objects are not accessible for read/write
       so we create this as a GpiObjType
    */
    if (is_static == vhpiGloballyStatic) {
        modifiable = false;
        logic = false;
        goto create;
    } else {
        modifiable = true;
        logic = false;
    }

    switch (base_type) {
        case vhpiSliceNameK:
        case vhpiIndexedNameK:
        case vhpiSelectedNameK: {
            vhpiHandleT sub_type = vhpi_handle(vhpiSubtype, new_hdl);
            if (base_hdl)
                vhpi_release_handle(base_hdl);

            base_hdl = vhpi_handle(vhpiBaseType, sub_type);
            query_hdl = base_hdl;
            /* Drop though */
        }
        case vhpiArrayTypeDeclK:
        case vhpiEnumTypeDeclK: {
            const char *type = vhpi_get_str(vhpiNameP, query_hdl);
            if (0 == strcmp(type, "STD_ULOGIC") ||
                0 == strcmp(type, "STD_LOGIC") ||
                0 == strncmp(type, "STD_ULOGIC_VECTOR", sizeof("STD_ULOGIC_VECTOR")-1) ||
                0 == strncmp(type, "STD_LOGIC_VECTOR", sizeof("STD_LOGIC_VECTOR")-1)) {
                LOG_DEBUG("Detected std_logic %s", fq_name.c_str());
                logic = true;
            } else if (0 == strcmp(type, "BOOLEAN") ||
                       0 == strcmp(type, "boolean") ||
                       0 == strcmp(type, "UNSIGNED")) {
                LOG_DEBUG("Detected boolean/integer %s", fq_name.c_str());
                gpi_type = GPI_INTEGER;
            } else if (0 == strncmp(type, "STRING", sizeof("STRING")-1)) {
                LOG_DEBUG("Detected a STRING type %s", fq_name.c_str());
                gpi_type = GPI_STRING;
            } else if (0 == strcmp(type, "CHARACTER") ||
                       0 == strcmp(type, "character")) {
                LOG_DEBUG("Detected an CHAR type %s", fq_name.c_str());
                gpi_type = GPI_INTEGER;
            } else {
                /* It not a standard type then we lastly try and use the format,
                   we do this on the handle we where given on a sub type */

                vhpiValueT value;
                value.format = vhpiObjTypeVal;
                value.bufSize = 0;
                value.numElems = 0;
                value.value.str = NULL;
                int num_elems = vhpi_get(vhpiSizeP, new_hdl);
                vhpi_get_value(new_hdl, &value);

                if (vhpiStrVal == value.format) {
                    LOG_DEBUG("Detected a STRING type %s", fq_name.c_str());
                    gpi_type = GPI_STRING;
                    break;
                } else if (vhpiRawDataVal == value.format ||
                           vhpiObjTypeVal == value.format) {
                    LOG_DEBUG("Detected a RAW type %s", fq_name.c_str());
                    gpi_type = GPI_MODULE;
                    break;
                } else if (vhpiCharVal == value.format) {
                    LOG_DEBUG("Detected an CHAR type %s", fq_name.c_str());
                    gpi_type = GPI_INTEGER;
                    break;
                }

                if (!value.numElems || (value.numElems == num_elems)) {
                    LOG_DEBUG("Detected single dimension vector type", fq_name.c_str());
                    gpi_type = GPI_ARRAY;
                } else {
                    LOG_DEBUG("Detected an n dimension valueector type", fq_name.c_str());
                    gpi_type = GPI_MODULE;
                    modifiable = false;
                }
            }

            break;
        }

        case vhpiIntTypeDeclK: {
            LOG_DEBUG("Detected an INT type %s", fq_name.c_str());
            gpi_type = GPI_INTEGER;
            break;
        }

        case vhpiFloatTypeDeclK: {
            LOG_DEBUG("Detected a REAL type %s", fq_name.c_str());
            gpi_type = GPI_REAL;
            break;
        }

        case vhpiForGenerateK:
        case vhpiIfGenerateK:
        case vhpiCompInstStmtK:
        case vhpiProcessStmtK:
        case vhpiSimpleSigAssignStmtK:
        case vhpiCondSigAssignStmtK:
        case vhpiRecordTypeDeclK:
        case vhpiSelectSigAssignStmtK:
            modifiable = false;
            break;

        default: {
            LOG_ERROR("Not able to map type (%s) %u to object",
                      vhpi_get_str(vhpiKindStrP, query_hdl), type);
            new_obj = NULL;
            goto out;
        }
    }

create:
    if (modifiable) {
        if (logic)
            new_obj = new VhpiLogicSignalObjHdl(this, new_hdl, gpi_type, is_const(type));
        else
            new_obj = new VhpiSignalObjHdl(this, new_hdl, gpi_type, is_const(type));
    }
    else
        new_obj = new GpiObjHdl(this, new_hdl, gpi_type);

    if (new_obj->initialise(name, fq_name)) {
        delete new_obj;
        new_obj = NULL;
    }

out:
    if (base_hdl)
        vhpi_release_handle(base_hdl);

    return new_obj;
}

GpiObjHdl *VhpiImpl::native_check_create(void *raw_hdl, GpiObjHdl *parent)
{
    LOG_DEBUG("Trying to convert raw to VHPI handle");

    vhpiHandleT new_hdl = (vhpiHandleT)raw_hdl;

    std::string fq_name = parent->get_fullname();
    const char *c_name = vhpi_get_str(vhpiNameP, new_hdl);
    if (!c_name) {
        LOG_DEBUG("Unable to query name of passed in handle");
        return NULL;
    }

    std::string name = c_name;

    if (fq_name == ":") {
        fq_name += name;
    } else {
        fq_name += "." + name;
    }

    GpiObjHdl* new_obj = create_gpi_obj_from_handle(new_hdl, name, fq_name);
    if (new_obj == NULL) {
        vhpi_release_handle(new_hdl);
        LOG_DEBUG("Unable to fetch object %s", fq_name.c_str());
        return NULL;
    }

    return new_obj;
}

GpiObjHdl *VhpiImpl::native_check_create(std::string &name, GpiObjHdl *parent)
{
    vhpiHandleT new_hdl;
    std::string fq_name = parent->get_fullname();
    if (fq_name == ":") {
        fq_name += name;
    } else {
        fq_name += "." + name;
    }
    std::vector<char> writable(fq_name.begin(), fq_name.end());
    writable.push_back('\0');

    new_hdl = vhpi_handle_by_name(&writable[0], NULL);

    if (new_hdl == NULL) {
        LOG_DEBUG("Unable to query vhpi_handle_by_name %s", fq_name.c_str());
        return NULL;
    }

    GpiObjHdl* new_obj = create_gpi_obj_from_handle(new_hdl, name, fq_name);
    if (new_obj == NULL) {
        vhpi_release_handle(new_hdl);
        LOG_DEBUG("Unable to fetch object %s", fq_name.c_str());
        return NULL;
    }

    return new_obj;
}

GpiObjHdl *VhpiImpl::native_check_create(uint32_t index, GpiObjHdl *parent)
{
    GpiObjHdl *parent_hdl = sim_to_hdl<GpiObjHdl*>(parent);
    vhpiHandleT vhpi_hdl = parent_hdl->get_handle<vhpiHandleT>();
    vhpiHandleT new_hdl;

    LOG_DEBUG("Native check create for index %u of parent %s (%s)",
              index,
              vhpi_get_str(vhpiNameP, vhpi_hdl),
              vhpi_get_str(vhpiKindStrP, vhpi_hdl));

    new_hdl = vhpi_handle_by_index(vhpiIndexedNames, vhpi_hdl, index);
    if (!new_hdl) {
        /* Support for the above seems poor, so if it did not work
           try an iteration instead */

        vhpiHandleT iter = vhpi_iterator(vhpiIndexedNames, vhpi_hdl);
        if (iter) {
            uint32_t curr_index = 0;
            while (true) {
                new_hdl = vhpi_scan(iter);
                if (!new_hdl) {
                    break;
                }
                if (index == curr_index) {
                    LOG_DEBUG("Index match %u == %u", curr_index, index);
                    break;
                }
                curr_index++;
            }
            vhpi_release_handle(iter);
        }
    }

    if (new_hdl == NULL) {
        LOG_DEBUG("Unable to query vhpi_handle_by_index %u", index);
        return NULL;
    }

    std::string name = vhpi_get_str(vhpiNameP, new_hdl);
    std::string fq_name = parent->get_fullname();
    if (fq_name == ":") {
        fq_name += name;
    } else {
        fq_name += "." + name;
    }
    GpiObjHdl* new_obj = create_gpi_obj_from_handle(new_hdl, name, fq_name);
    if (new_obj == NULL) {
        vhpi_release_handle(new_hdl);
        LOG_DEBUG("Could not fetch object below entity (%s) at index (%u)",
                  parent->get_name_str(), index);
        return NULL;
    }

    return new_obj;
}

GpiObjHdl *VhpiImpl::get_root_handle(const char* name)
{
    vhpiHandleT root = NULL;
    vhpiHandleT arch = NULL;
    vhpiHandleT dut = NULL;
    GpiObjHdl *rv = NULL;
    std::string root_name;
    const char *found;

    root = vhpi_handle(vhpiRootInst, NULL);
    check_vhpi_error();

    if (!root) {
        LOG_ERROR("VHPI: Attempting to get the vhpiRootInst failed");
        return NULL;
    } else {
        LOG_DEBUG("VHPI: We have found root='%s'", vhpi_get_str(vhpiCaseNameP, root));
    }

    if (name) {
        if (NULL == (dut = vhpi_handle_by_name(name, NULL))) {
            LOG_DEBUG("VHPI: Unable to query by name");
            check_vhpi_error();
        }
    }

    if (!dut) {
        if (NULL == (arch = vhpi_handle(vhpiDesignUnit, root))) {
            LOG_DEBUG("VHPI: Unable to get vhpiDesignUnit via root");
            check_vhpi_error();
            return NULL;
        }

        if (NULL == (dut = vhpi_handle(vhpiPrimaryUnit, arch))) {
            LOG_DEBUG("VHPI: Unable to get vhpiPrimaryUnit via arch");
            check_vhpi_error();
            return NULL;
        }

        /* if this matches the name then it is what we want, but we
           use the handle two levels up as the dut as do not want an
           object of type vhpiEntityDeclK as the dut */

        found = vhpi_get_str(vhpiCaseNameP, dut);
        dut = root;

    } else {
        found = vhpi_get_str(vhpiCaseNameP, dut);
    }

    if (!dut) {
        LOG_ERROR("VHPI: Attempting to get the DUT handle failed");
        return NULL;
    }

    if (!found) {
        LOG_ERROR("VHPI: Unable to query name for DUT handle");
        return NULL;
    }

    if (name != NULL && strcmp(name, found)) {
        LOG_WARN("VHPI: DUT '%s' doesn't match requested toplevel %s", found, name);
        return NULL;
    }

    root_name = found;
    rv = new GpiObjHdl(this, dut, to_gpi_objtype(vhpi_get(vhpiKindP, dut)));
    rv->initialise(root_name, root_name);

    return rv;
}

GpiIterator *VhpiImpl::iterate_handle(GpiObjHdl *obj_hdl, gpi_iterator_sel_t type)
{
    GpiIterator *new_iter = NULL;

    switch (type) {
        case GPI_OBJECTS:
            new_iter = new VhpiIterator(this, obj_hdl);
            break;
        default:
            LOG_WARN("Other iterator types not implemented yet");
            break;
    }
    return new_iter;
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
