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


#include "../gpi/gpi_priv.h"
#include <vhpi_user.h>

#define VHPI_CHECKING 1

extern "C" {
void handle_vhpi_callback(const vhpiCbDataT *cb_data);
int __check_vhpi_error(const char *func, long line);
const char * vhpi_format_to_string(int reason);
const vhpiEnumT chr2vhpi(const char value);
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

// Should be run after every VPI call to check error status
int __check_vhpi_error(const char *func, long line)
{
    int level=0;
#if VHPI_CHECKING
    vhpiErrorInfoT info;
    int loglevel;
    level = vhpi_check_error(&info);
    if (level == 0)
        return 0;

    switch (level) {
        case vhpiNote:
            loglevel = GPIInfo;
            break;
        case vhpiWarning:
            loglevel = GPIWarning;
            break;
        case vhpiError:
            loglevel = GPIError;
            break;
        case vhpiFailure:
        case vhpiSystem:
        case vhpiInternal:
            loglevel = GPICritical;
            break;
    }

    gpi_log("cocotb.gpi", loglevel, __FILE__, func, line,
            "VHPI Error level %d: %s\nFILE %s:%d",
            info.severity, info.message, info.file, info.line);

#endif
    return level;
}

#define check_vhpi_error() \
    __check_vhpi_error(__func__, __LINE__)

class vhpi_obj_hdl : public gpi_obj_hdl {
private:
    int m_size;
    vhpiValueT m_value;
public:
    vhpi_obj_hdl(vhpiHandleT hdl, gpi_impl_interface *impl) : gpi_obj_hdl(impl),
                                                              m_size(0),
                                                              vhpi_hdl(hdl) { }
    virtual ~vhpi_obj_hdl() {
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

class vhpi_cb_hdl : public gpi_cb_hdl {
protected:
    vhpiCbDataT cb_data;
    vhpiHandleT vhpi_hdl;
public:
    vhpi_cb_hdl(gpi_impl_interface *impl) : gpi_cb_hdl(impl) {
        cb_data.reason    = 0;
        cb_data.cb_rtn    = handle_vhpi_callback;
        cb_data.obj       = NULL;
        cb_data.time      = NULL;
        cb_data.value     = NULL;
        cb_data.user_data = (char *)this;
    }

    int arm_callback(void) {
        vhpiHandleT new_hdl = vhpi_register_cb(&cb_data, vhpiReturnCb);
        int ret = 0;

        if (!new_hdl) {
            LOG_CRITICAL("VHPI: Unable to register callback a handle for VHPI type %s(%d)",
                         reason_to_string(cb_data.reason), cb_data.reason);
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
    };

    int cleanup_callback(void) {
        vhpiStateT cbState = (vhpiStateT)vhpi_get(vhpiStateP, vhpi_hdl);
        if (vhpiMature == cbState)
            return vhpi_remove_cb(vhpi_hdl);
        return 0;
    }

    const char *reason_to_string(int reason) {
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

};

class vhpi_cb_startup : public vhpi_cb_hdl {
public:
    vhpi_cb_startup(gpi_impl_interface *impl) : vhpi_cb_hdl(impl) { 
        cb_data.reason = vhpiCbStartOfSimulation;
    }

    int run_callback(void) {
        FENTER
        gpi_sim_info_t sim_info;
        sim_info.argc = 0;
        sim_info.argv = NULL;
        sim_info.product = gpi_copy_name(vhpi_get_str(vhpiNameP, NULL));
        sim_info.version = gpi_copy_name(vhpi_get_str(vhpiToolVersionP, NULL));
        gpi_embed_init(&sim_info);

        free(sim_info.product);
        free(sim_info.version);
        
        FEXIT

        return 0;
    }
};

class vhpi_cb_shutdown : public vhpi_cb_hdl {
public:
    vhpi_cb_shutdown(gpi_impl_interface *impl) : vhpi_cb_hdl(impl) { 
        cb_data.reason = vhpiCbEndOfSimulation;
    } 
    int run_callback(void) {
        gpi_embed_end();
        return 0;
    }
};

class vhpi_cb_timed : public vhpi_cb_hdl {
private:
vhpiTimeT time;
public:
    vhpi_cb_timed(gpi_impl_interface *impl, uint64_t time_ps) : vhpi_cb_hdl(impl) {
        time.high = (uint32_t)(time_ps>>32);
        time.low  = (uint32_t)(time_ps); 

        cb_data.reason = vhpiCbAfterDelay;
        cb_data.time = &time;
    }
};


class vhpi_impl : public gpi_impl_interface {
public:
    vhpi_impl(const string& name) : gpi_impl_interface(name) { }

     /* Sim related */
    void sim_end(void) { }
    void get_sim_time(uint32_t *high, uint32_t *low) { }

    /* Signal related */
    gpi_obj_hdl *get_root_handle(const char *name);
    gpi_obj_hdl *get_handle_by_name(const char *name, gpi_obj_hdl *parent) { return NULL; }
    gpi_obj_hdl *get_handle_by_index(gpi_obj_hdl *parent, uint32_t index) { return NULL; }
    void free_handle(gpi_obj_hdl*) { }
    gpi_iterator *iterate_handle(uint32_t type, gpi_obj_hdl *base) { return NULL; }
    gpi_obj_hdl *next_handle(gpi_iterator *iterator) { return NULL; }
    char* get_signal_value_binstr(gpi_obj_hdl *gpi_hdl) { return NULL; }
    char* get_signal_name_str(gpi_obj_hdl *gpi_hdl);
    char* get_signal_type_str(gpi_obj_hdl *gpi_hdl);
    void set_signal_value_int(gpi_obj_hdl *gpi_hdl, int value);
    void set_signal_value_str(gpi_obj_hdl *gpi_hdl, const char *str);    // String of binary char(s) [1, 0, x, z]
    
    /* Callback related */
    gpi_cb_hdl *register_timed_callback(uint64_t time_ps);
    gpi_cb_hdl *register_value_change_callback(gpi_obj_hdl *obj_hdl) { return NULL; }
    gpi_cb_hdl *register_readonly_callback(void) { return NULL; }
    gpi_cb_hdl *register_nexttime_callback(void) { return NULL; }
    gpi_cb_hdl *register_readwrite_callback(void) { return NULL; }
    int deregister_callback(gpi_cb_hdl *gpi_hdl) { return 0; }

    gpi_cb_hdl *create_cb_handle(void) { return NULL; }
    void destroy_cb_handle(gpi_cb_hdl *gpi_hdl) { }
};

// Handle related functions
/**
 * @name    Find the root handle
 * @brief   Find the root handle using a optional name
 *
 * Get a handle to the root simulator object.  This is usually the toplevel.
 *
 * FIXME: In VHPI we always return the first root instance
 * 
 * TODO: Investigate possibility of iterating and checking names as per VHPI
 * If no name is defined, we return the first root instance.
 *
 * If name is provided, we check the name against the available objects until
 * we find a match.  If no match is found we return NULL
 */
gpi_obj_hdl *vhpi_impl::get_root_handle(const char* name)
{
    FENTER
    vhpiHandleT root;
    vhpiHandleT dut;
    gpi_obj_hdl *rv;

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

    rv = new vhpi_obj_hdl(root, this);

    FEXIT
    return rv;
}

char *vhpi_impl::get_signal_name_str(gpi_obj_hdl *gpi_hdl)
{
    FENTER
    vhpi_obj_hdl *vhpi_obj = reinterpret_cast<vhpi_obj_hdl*>(gpi_hdl);
    const char *name = vhpi_get_str(vhpiFullNameP, vhpi_obj->vhpi_hdl);
    check_vhpi_error();
    char *result = vhpi_obj->gpi_copy_name(name);
    LOG_WARN("Signal name was %s", name);
    FEXIT
    return result;
}

char *vhpi_impl::get_signal_type_str(gpi_obj_hdl *gpi_hdl)
{
    FENTER
    vhpi_obj_hdl *vhpi_obj = reinterpret_cast<vhpi_obj_hdl*>(gpi_hdl);
    const char *name = vhpi_get_str(vhpiKindStrP, vhpi_obj->vhpi_hdl);
    check_vhpi_error();
    char *result = vhpi_obj->gpi_copy_name(name);
    LOG_WARN("Signal type was %s", name);
    FEXIT
    return result;
}

gpi_cb_hdl *vhpi_impl::register_timed_callback(uint64_t time_ps)
{
    vhpi_cb_timed *hdl = new vhpi_cb_timed(this, time_ps);

    if (hdl->arm_callback()) {
        delete(hdl);
        hdl = NULL;
    }

    return hdl;
}

// Unfortunately it seems that format conversion is not well supported
// We have to set values using vhpiEnum*
void vhpi_impl::set_signal_value_int(gpi_obj_hdl *gpi_hdl, int value)
{
    FENTER

    vhpi_obj_hdl *vhpi_obj = reinterpret_cast<vhpi_obj_hdl*>(gpi_hdl);
    vhpi_obj->write_new_value(value);

    FEXIT
}

void vhpi_impl::set_signal_value_str(gpi_obj_hdl *gpi_hdl, const char *str)
{
    FENTER

    vhpi_obj_hdl *vhpi_obj = reinterpret_cast<vhpi_obj_hdl*>(gpi_hdl);
    vhpi_obj->write_new_value(str);

    FEXIT
}

extern "C" {

static vhpi_cb_hdl *sim_init_cb;
static vhpi_cb_hdl *sim_finish_cb;
static vhpi_impl *vhpi_table;


// Main entry point for callbacks from simulator
void handle_vhpi_callback(const vhpiCbDataT *cb_data)
{
    FENTER

    vhpi_cb_hdl *cb_hdl = (vhpi_cb_hdl*)cb_data->user_data;

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
    sim_init_cb = new vhpi_cb_startup(vhpi_table);
    sim_init_cb->arm_callback();
    FEXIT
}

static void register_final_callback(void)
{
    FENTER
    sim_finish_cb = new vhpi_cb_shutdown(vhpi_table);
    sim_finish_cb->arm_callback();
    FEXIT
}

static void register_embed(void)
{
    vhpi_table = new vhpi_impl("VHPI");
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