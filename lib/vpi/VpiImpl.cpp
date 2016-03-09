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
*    * Neither the name of Potential Ventures Ltd
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

extern "C" {

static VpiCbHdl *sim_init_cb;
static VpiCbHdl *sim_finish_cb;
static VpiImpl *vpi_table;

}

const char *VpiImpl::reason_to_string(int reason)
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

void VpiImpl::get_sim_time(uint32_t *high, uint32_t *low)
{
    s_vpi_time vpi_time_s;
    vpi_time_s.type = vpiSimTime;       //vpiSimTime;
    vpi_get_time(NULL, &vpi_time_s);
    check_vpi_error();
    *high = vpi_time_s.high;
    *low = vpi_time_s.low;
}

gpi_objtype_t to_gpi_objtype(int32_t vpitype)
{
    switch (vpitype) {
        case vpiNet:
        case vpiNetBit:
        case vpiReg:
        case vpiRegBit:
            return GPI_REGISTER;

        case vpiRealVar:
            return GPI_REAL;

        case vpiInterfaceArray:
        case vpiPackedArrayVar:
        case vpiRegArray:
        case vpiNetArray:
        case vpiGenScopeArray:
            return GPI_ARRAY;

        case vpiEnumNet:
        case vpiEnumVar:
            return GPI_ENUM;

        case vpiIntVar:
        case vpiIntegerVar:
        case vpiIntegerNet:
            return GPI_INTEGER;

        case vpiParameter:
            return GPI_PARAMETER;


        case vpiStructVar:
        case vpiStructNet:
            return GPI_STRUCTURE;

        case vpiModport:
        case vpiInterface:
        case vpiModule:
        case vpiRefObj:
        case vpiPort:
        case vpiAlways:
        case vpiFunction:
        case vpiInitial:
        case vpiGate:
        case vpiPrimTerm:
        case vpiGenScope:
            return GPI_MODULE;

        case vpiStringVal:
            return GPI_STRING;

        default:
            LOG_DEBUG("Unable to map VPI type %d onto GPI type", vpitype);
            return GPI_UNKNOWN;
    }
}

GpiObjHdl* VpiImpl::create_gpi_obj_from_handle(vpiHandle new_hdl,
                                               std::string &name,
                                               std::string &fq_name)
{
    int32_t type;
    GpiObjHdl *new_obj = NULL;
    if (vpiUnknown == (type = vpi_get(vpiType, new_hdl))) {
        LOG_DEBUG("vpiUnknown returned from vpi_get(vpiType, ...)")
        return NULL;
    }

    /* What sort of instance is this ?*/
    switch (type) {
        case vpiNet:
        case vpiNetBit:
        case vpiReg:
        case vpiRegBit:
        case vpiRegArray:
        case vpiNetArray:
        case vpiEnumNet:
        case vpiEnumVar:
        case vpiIntVar:
        case vpiIntegerVar:
        case vpiIntegerNet:
        case vpiRealVar:
            new_obj = new VpiSignalObjHdl(this, new_hdl, to_gpi_objtype(type), false);
            break;
        case vpiParameter:
            new_obj = new VpiSignalObjHdl(this, new_hdl, to_gpi_objtype(type), true);
            break;
        case vpiStructVar:
        case vpiStructNet:
        case vpiModule:
        case vpiInterface:
        case vpiModport:
        case vpiInterfaceArray:
        case vpiRefObj:
        case vpiPackedArrayVar:
        case vpiPort:
        case vpiAlways:
        case vpiFunction:
        case vpiInitial:
        case vpiGate:
        case vpiPrimTerm:
        case vpiGenScope:
        case vpiGenScopeArray:
            new_obj = new GpiObjHdl(this, new_hdl, to_gpi_objtype(type));
            break;
        default:
            /* We should only print a warning here if the type is really verilog,
               It could be vhdl as some simulators allow qurying of both languages
               via the same handle
               */
            const char *type_name = vpi_get_str(vpiType, new_hdl);
            std::string unknown = "vpiUnknown";
            if (type_name && (unknown != type_name)) {
                LOG_DEBUG("VPI: Not able to map type %s(%d) to object.", type_name, type);
            } else {
                LOG_DEBUG("VPI: Simulator does not know this type (%d) via VPI", type);
            }
            return NULL;
    }

    new_obj->initialise(name, fq_name);

    LOG_DEBUG("VPI: Created object with type was %s(%d)",
              vpi_get_str(vpiType, new_hdl), type);

    return new_obj;
}

GpiObjHdl* VpiImpl::native_check_create(void *raw_hdl, GpiObjHdl *parent)
{
    LOG_DEBUG("Trying to convert raw to VPI handle");

    vpiHandle new_hdl = (vpiHandle)raw_hdl;

    const char *c_name = vpi_get_str(vpiName, new_hdl);
    if (!c_name) {
        LOG_DEBUG("Unable to query name of passed in handle");
        return NULL;
    }

    std::string name = c_name;
    std::string fq_name = parent->get_fullname() + "." + name;

    GpiObjHdl* new_obj = create_gpi_obj_from_handle(new_hdl, name, fq_name);
    if (new_obj == NULL) {
        vpi_free_object(new_hdl);
        LOG_DEBUG("Unable to fetch object %s", fq_name.c_str());
        return NULL;
    }
    return new_obj;
}

GpiObjHdl* VpiImpl::native_check_create(std::string &name, GpiObjHdl *parent)
{
    vpiHandle new_hdl;
    std::string fq_name = parent->get_fullname() + "." + name;
    std::vector<char> writable(fq_name.begin(), fq_name.end());
    writable.push_back('\0');

    new_hdl = vpi_handle_by_name(&writable[0], NULL);
    if (new_hdl == NULL) {
        LOG_DEBUG("Unable to query vpi_get_handle_by_name %s", fq_name.c_str());
        return NULL;
    }
    GpiObjHdl* new_obj = create_gpi_obj_from_handle(new_hdl, name, fq_name);
    if (new_obj == NULL) {
        vpi_free_object(new_hdl);
        LOG_DEBUG("Unable to fetch object %s", fq_name.c_str());
        return NULL;
    }
    return new_obj;
}

GpiObjHdl* VpiImpl::native_check_create(uint32_t index, GpiObjHdl *parent)
{
    GpiObjHdl *parent_hdl = sim_to_hdl<GpiObjHdl*>(parent);
    vpiHandle vpi_hdl = parent_hdl->get_handle<vpiHandle>();
    vpiHandle new_hdl;

    new_hdl = vpi_handle_by_index(vpi_hdl, index);
    if (new_hdl == NULL) {
        LOG_DEBUG("Unable to vpi_get_handle_by_index %s[%u]", vpi_get_str(vpiName, vpi_hdl), index);
        return NULL;
    }

    std::string name = vpi_get_str(vpiName, new_hdl);
    std::string fq_name = parent->get_fullname() + "." + name;
    GpiObjHdl* new_obj = create_gpi_obj_from_handle(new_hdl, name, fq_name);
    if (new_obj == NULL) {
        vpi_free_object(new_hdl);
        LOG_DEBUG("Unable to fetch object below entity (%s) at index (%u)",
                  parent->get_name_str(), index);
        return NULL;
    }
    return new_obj;
}

GpiObjHdl *VpiImpl::get_root_handle(const char* name)
{
    vpiHandle root;
    vpiHandle iterator;
    GpiObjHdl *rv;
    std::string root_name;

    // vpi_iterate with a ref of NULL returns the top level module
    iterator = vpi_iterate(vpiModule, NULL);
    check_vpi_error();
    if (!iterator) {
        LOG_INFO("Nothing visible via VPI");
        return NULL;
    }

    for (root = vpi_scan(iterator); root != NULL; root = vpi_scan(iterator)) {

        if (name == NULL || !strcmp(name, vpi_get_str(vpiFullName, root)))
            break;
    }

    if (!root) {
        check_vpi_error();
        goto error;
    }

    //Need to free the iterator if it didn't return NULL
    if (iterator && !vpi_free_object(iterator)) {
        LOG_WARN("VPI: Attempting to free root iterator failed!");
        check_vpi_error();
    }

    root_name = vpi_get_str(vpiFullName, root);
    rv = new GpiObjHdl(this, root, to_gpi_objtype(vpi_get(vpiType, root)));
    rv->initialise(root_name, root_name);

    return rv;

  error:

    LOG_ERROR("VPI: Couldn't find root handle %s", name);

    iterator = vpi_iterate(vpiModule, NULL);

    for (root = vpi_scan(iterator); root != NULL; root = vpi_scan(iterator)) {

        LOG_ERROR("VPI: Toplevel instances: %s != %s...", name, vpi_get_str(vpiFullName, root));

        if (name == NULL || !strcmp(name, vpi_get_str(vpiFullName, root)))
            break;
    }

    return NULL;
}

GpiIterator *VpiImpl::iterate_handle(GpiObjHdl *obj_hdl, gpi_iterator_sel_t type)
{
    GpiIterator *new_iter;
    switch (type) {
        case GPI_OBJECTS:
            new_iter = new VpiIterator(this, obj_hdl);
            break;
        case GPI_DRIVERS:
            new_iter = new VpiSingleIterator(this, obj_hdl, vpiDriver);
            break;
        case GPI_LOADS:
            new_iter = new VpiSingleIterator(this, obj_hdl, vpiLoad);
            break;
        default:
            LOG_WARN("Other iterator types not implemented yet");
            break;
    }
    return new_iter;
}

GpiCbHdl *VpiImpl::register_timed_callback(uint64_t time_ps)
{
    VpiTimedCbHdl *hdl = new VpiTimedCbHdl(this, time_ps);

    if (hdl->arm_callback()) {
        delete(hdl);
        hdl = NULL;
    }

    return hdl;
}

GpiCbHdl *VpiImpl::register_readwrite_callback(void)
{
    if (m_read_write.arm_callback())
        return NULL;

    return &m_read_write;
}

GpiCbHdl *VpiImpl::register_readonly_callback(void)
{
    if (m_read_only.arm_callback())
        return NULL;

    return &m_read_only;
}

GpiCbHdl *VpiImpl::register_nexttime_callback(void)
{
    if (m_next_phase.arm_callback())
        return NULL;

    return &m_next_phase;
}

int VpiImpl::deregister_callback(GpiCbHdl *gpi_hdl)
{
    gpi_hdl->cleanup_callback();
    return 0;
}

// If the Pything world wants things to shut down then unregister
// the callback for end of sim
void VpiImpl::sim_end(void)
{
    /* Some sims do not seem to be able to deregister the end of sim callback
     * so we need to make sure we have tracked this and not call the handler
     */
    if (GPI_DELETE != sim_finish_cb->get_call_state()) {
        sim_finish_cb->set_call_state(GPI_DELETE);
        vpi_control(vpiFinish);
        check_vpi_error();
    }
}

extern "C" {

// Main re-entry point for callbacks from simulator
int32_t handle_vpi_callback(p_cb_data cb_data)
{
    int rv = 0;

    VpiCbHdl *cb_hdl = (VpiCbHdl*)cb_data->user_data;

    if (!cb_hdl) {
        LOG_CRITICAL("VPI: Callback data corrupted: ABORTING");
    }

    gpi_cb_state_e old_state = cb_hdl->get_call_state();

    if (old_state == GPI_PRIMED) {

        cb_hdl->set_call_state(GPI_CALL);
        cb_hdl->run_callback();

        gpi_cb_state_e new_state = cb_hdl->get_call_state();

        /* We have re-primed in the handler */
        if (new_state != GPI_PRIMED)
            if (cb_hdl->cleanup_callback())
                delete cb_hdl;

    } else {
        /* Issue #188: This is a work around for a modelsim */
        if (cb_hdl->cleanup_callback())
            delete cb_hdl;
    }

    return rv;
};


static void register_embed(void)
{
    vpi_table = new VpiImpl("VPI");
    gpi_register_impl(vpi_table);
    gpi_load_extra_libs();
}


static void register_initial_callback(void)
{
    sim_init_cb = new VpiStartupCbHdl(vpi_table);
    sim_init_cb->arm_callback();
}

static void register_final_callback(void)
{
    sim_finish_cb = new VpiShutdownCbHdl(vpi_table);
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
        vpi_scan(args_iter);
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
        gpi_embed_event(SIM_TEST_FAIL, argval.value.str);

    return 0;
}

static void register_system_functions(void)
{
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

GPI_ENTRY_POINT(vpi, register_embed)
