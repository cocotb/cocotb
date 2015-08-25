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

extern "C" int32_t handle_vpi_callback(p_cb_data cb_data);

VpiCbHdl::VpiCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl)
{

    vpi_time.high = 0;
    vpi_time.low = 0;
    vpi_time.type = vpiSimTime;

    cb_data.reason    = 0;
    cb_data.cb_rtn    = handle_vpi_callback;
    cb_data.obj       = NULL;
    cb_data.time      = &vpi_time;
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

    // Only a problem if we have not been asked to deregister and register
    // in the same simultion callback
    if (m_obj_hdl != NULL && m_state != GPI_DELETE) {
        fprintf(stderr,
                "We seem to already be registered, deregistering %s!\n",
                m_impl->reason_to_string(cb_data.reason));
        cleanup_callback();
    }

    vpiHandle new_hdl = vpi_register_cb(&cb_data);
    check_vpi_error();
    
    int ret = 0;

    if (!new_hdl) {
        LOG_CRITICAL("VPI: Unable to register a callback handle for VPI type %s(%d)",
                     m_impl->reason_to_string(cb_data.reason), cb_data.reason);
        
        ret = -1;
    } else {
        m_state = GPI_PRIMED;
    }
    
    m_obj_hdl = new_hdl;

    return ret;
}

int VpiCbHdl::cleanup_callback(void)
{
    if (m_state == GPI_FREE)
        return 0;

    /* If the one-time callback has not come back then
     * remove it, it is has then free it. The remove is done
     * internally */

    if (m_state == GPI_PRIMED) {
        if (!m_obj_hdl) {
            LOG_CRITICAL("VPI: passed a NULL pointer : ABORTING");
            exit(1);
        }

        if (!(vpi_remove_cb(get_handle<vpiHandle>()))) {
            LOG_CRITICAL("VPI: unbale to remove callback : ABORTING");
            exit(1);
        }

        check_vpi_error();
    } else {
#ifndef MODELSIM
        /* This is disabled for now, causes a small leak going to put back in */
        if (!(vpi_free_object(get_handle<vpiHandle>()))) {
            LOG_CRITICAL("VPI: unbale to free handle : ABORTING");
            exit(1);
        }
#endif
    }


    m_obj_hdl = NULL;
    m_state = GPI_FREE;

    return 0;
}

int VpiSignalObjHdl::initialise(std::string &name) {
    m_num_elems = vpi_get(vpiSize, GpiObjHdl::get_handle<vpiHandle>());
    LOG_DEBUG("VPI: %s initialised with %d elements", name.c_str(), m_num_elems);
    return GpiObjHdl::initialise(name);
}

const char* VpiSignalObjHdl::get_signal_value_binstr(void)
{
    FENTER
    s_vpi_value value_s = {vpiBinStrVal};

    vpi_get_value(GpiObjHdl::get_handle<vpiHandle>(), &value_s);
    check_vpi_error();

    return value_s.value.str;
}

double VpiSignalObjHdl::get_signal_value_real(void)
{
    FENTER
    s_vpi_value value_s = {vpiRealVal};

    vpi_get_value(GpiObjHdl::get_handle<vpiHandle>(), &value_s);
    check_vpi_error();

    return value_s.value.real;
}

long VpiSignalObjHdl::get_signal_value_long(void)
{
    FENTER
    s_vpi_value value_s = {vpiIntVal};

    vpi_get_value(GpiObjHdl::get_handle<vpiHandle>(), &value_s);
    check_vpi_error();

    return value_s.value.integer;
}

// Value related functions
int VpiSignalObjHdl::set_signal_value(long value)
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
    vpi_put_value(GpiObjHdl::get_handle<vpiHandle>(), &value_s, &vpi_time_s, vpiInertialDelay);
    check_vpi_error();

    FEXIT
    return 0;
}

int VpiSignalObjHdl::set_signal_value(double value)
{
    FENTER
    s_vpi_value value_s;

    value_s.value.real = value;
    value_s.format = vpiRealVal;

    s_vpi_time vpi_time_s;

    vpi_time_s.type = vpiSimTime;
    vpi_time_s.high = 0;
    vpi_time_s.low  = 0;

    vpi_put_value(GpiObjHdl::get_handle<vpiHandle>(), &value_s, &vpi_time_s, vpiInertialDelay);
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

    vpi_put_value(GpiObjHdl::get_handle<vpiHandle>(), &value_s, NULL, vpiNoDelay);
    check_vpi_error();

    FEXIT
    return 0;
}

GpiCbHdl * VpiSignalObjHdl::value_change_cb(unsigned int edge)
{
    VpiValueCbHdl *cb = NULL;

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

VpiValueCbHdl::VpiValueCbHdl(GpiImplInterface *impl,
                             VpiSignalObjHdl *sig,
                             int edge) :GpiCbHdl(impl), 
                                        VpiCbHdl(impl),
                                        GpiValueCbHdl(impl,sig,edge)
{
    vpi_time.type = vpiSuppressTime;
    m_vpi_value.format = vpiIntVal;

    cb_data.reason = cbValueChange;
    cb_data.time = &vpi_time;
    cb_data.value = &m_vpi_value;
    cb_data.obj = m_signal->get_handle<vpiHandle>();
}

int VpiValueCbHdl::cleanup_callback(void)
{
    if (m_state == GPI_FREE)
        return 0;

    /* This is a recurring callback so just remove when
     * not wanted */
    if (!(vpi_remove_cb(get_handle<vpiHandle>()))) {
        LOG_CRITICAL("VPI: unbale to remove callback : ABORTING");
        exit(1);
    }

    m_obj_hdl = NULL;
    m_state = GPI_FREE;
    return 0;
}

VpiStartupCbHdl::VpiStartupCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                                           VpiCbHdl(impl)
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

VpiShutdownCbHdl::VpiShutdownCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                                             VpiCbHdl(impl)
{
    cb_data.reason = cbEndOfSimulation;
}

int VpiShutdownCbHdl::run_callback(void) {
    gpi_embed_end();
    return 0;
}

VpiTimedCbHdl::VpiTimedCbHdl(GpiImplInterface *impl, uint64_t time_ps) : GpiCbHdl(impl),
                                                                         VpiCbHdl(impl)
{
    vpi_time.high = (uint32_t)(time_ps>>32);
    vpi_time.low  = (uint32_t)(time_ps);
    vpi_time.type = vpiSimTime;

    cb_data.reason = cbAfterDelay;
}

int VpiTimedCbHdl::cleanup_callback(void)
{
    switch (m_state) {
    case GPI_PRIMED:
        /* Issue #188: Work around for modelsim that is harmless to othes too,
           we tag the time as delete, let it fire then do not pass up
           */
        LOG_DEBUG("Not removing PRIMED timer %d\n",vpi_time.low);
        m_state = GPI_DELETE;
        return 0;
    case GPI_DELETE:
        LOG_DEBUG("Removing DELETE timer %d\n",vpi_time.low);
    default:
        break;
    }
    VpiCbHdl::cleanup_callback();
    /* Return one so we delete this object */
    return 1;
}

VpiReadwriteCbHdl::VpiReadwriteCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                                               VpiCbHdl(impl)
{
    cb_data.reason = cbReadWriteSynch;
    delay_kill = false;
}

VpiReadOnlyCbHdl::VpiReadOnlyCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                                             VpiCbHdl(impl)
{
    cb_data.reason = cbReadOnlySynch;
}

VpiNextPhaseCbHdl::VpiNextPhaseCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                                               VpiCbHdl(impl)
{
    cb_data.reason = cbNextSimTime;
}

KindMappings::KindMappings()
{
    /* vpiModule */
    int32_t module_options[] = {
        //vpiModule,  add this back
        vpiContAssign,
        vpiDefParam,
        vpiMemory,
        vpiModPath,
        vpiNamedEvent,
        vpiNet,
        //vpiParamAssign,Aldec does not support this - SEGV
        vpiParameter,
        vpiPort,
        vpiReg,
        vpiSpecParam,
        vpiTchk,
        vpiAttribute,
        //vpiModuleArray, Aldec does not support this - SEGV
        vpiPrimitiveArray,
        vpiNetArray,
        vpiRegArray,
        vpiNamedEventArray,
        //vpiInterface, Aldec does not support this - SEGV
        //vpiInterfaceArray, Aldec does not support this - SEGV
        0
    };
    add_to_options(vpiModule, &module_options[0]);
    /* vpiNet */
    int32_t net_options[] = {
        0
    };
    add_to_options(vpiNet, &net_options[0]);
    /* vpiPort */
    int32_t port_options[] = {
        vpiAttribute,
        0
    };
    add_to_options(vpiPort, &port_options[0]);
}

void KindMappings::add_to_options(int32_t type, int32_t *options)
{
    std::vector<int32_t> option_vec;
    int32_t *ptr = options;
    while (*ptr) {
        option_vec.push_back(*ptr);
        ptr++;
    }
    options_map[type] = option_vec;
}

std::vector<int32_t>* KindMappings::get_options(int32_t type)
{
    std::map<int32_t, std::vector<int32_t> >::iterator valid = options_map.find(type);

    if (options_map.end() == valid) {
        LOG_ERROR("VPI: Implementation does not know how to iterate over %d", type);
        exit(1);
    } else {
        return &valid->second;
    }
}

KindMappings VpiIterator::iterate_over;

VpiIterator::VpiIterator(GpiImplInterface *impl, vpiHandle hdl) : GpiIterator(impl, hdl),
                                                                  m_iterator(NULL)
{
    vpiHandle iterator;

    selected = iterate_over.get_options(vpi_get(vpiType, hdl));

    for (one2many = selected->begin();
         one2many != selected->end();
         one2many++) {
        iterator = vpi_iterate(*one2many, hdl);

        if (iterator) {
            break;
        }
     
        LOG_DEBUG("vpi_iterate type=%d returned NULL", *one2many);
    }

    if (NULL == iterator) {
        LOG_WARN("vpi_iterate returned NULL for all types");
        return;
    }

    LOG_DEBUG("Created iterator working from type %d",
              *one2many,
              vpi_get_str(vpiFullName, hdl));

    m_iterator = iterator;
}

VpiIterator::~VpiIterator()
{
    if (m_iterator)
        vpi_free_object(m_iterator);

    LOG_DEBUG("Deleted VpiIterator");
}

GpiObjHdl *VpiIterator::next_handle(void)
{
    vpiHandle obj;
    GpiObjHdl *new_obj = NULL;

    do {
        obj = NULL;

        if (m_iterator) {
            obj = vpi_scan(m_iterator);

            if (NULL == obj) {
                /* m_iterator will already be free'd internally here */
                m_iterator = NULL;
            } else {
                break;
            }

            LOG_DEBUG("End of type=%d iteration", *one2many);
        } else {
            LOG_DEBUG("No valid type=%d iterator", *one2many);
        }

        if (++one2many >= selected->end()) {
            obj = NULL;
            break;
        }

        m_iterator = vpi_iterate(*one2many, get_handle<vpiHandle>());

    } while (!obj);

    if (NULL == obj) {
        LOG_DEBUG("No more children, all relationships tested");
        return new_obj;
    }

    std::string name;
    if (vpiPort == vpi_get(vpiType, obj))
        name = vpi_get_str(vpiName, obj);
    else
        name = name = vpi_get_str(vpiName, obj);

    LOG_DEBUG("vpi_scan found name:%s", name.c_str());

    VpiImpl *vpi_impl = reinterpret_cast<VpiImpl*>(m_impl);
    new_obj = vpi_impl->create_gpi_obj_from_handle(obj, name);
    return new_obj;
}
