/******************************************************************************
 * Copyright (c) 2013, 2018 Potential Ventures Ltd
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
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
 * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 ******************************************************************************/

#include <assert.h>

#include <stdexcept>

#include "VpiImpl.h"

extern "C" int32_t handle_vpi_callback(p_cb_data cb_data);

VpiCbHdl::VpiCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl) {
    vpi_time.high = 0;
    vpi_time.low = 0;
    vpi_time.type = vpiSimTime;

    cb_data.reason = 0;
    cb_data.cb_rtn = handle_vpi_callback;
    cb_data.obj = NULL;
    cb_data.time = &vpi_time;
    cb_data.value = NULL;
    cb_data.index = 0;
    cb_data.user_data = (char *)this;
}

/* If the user data already has a callback handle then deregister
 * before getting the new one
 */
int VpiCbHdl::arm_callback() {
    if (m_state == GPI_PRIMED) {
        fprintf(stderr, "Attempt to prime an already primed trigger for %s!\n",
                m_impl->reason_to_string(cb_data.reason));
    }

    // Only a problem if we have not been asked to deregister and register
    // in the same simulation callback
    if (m_obj_hdl != NULL && m_state != GPI_DELETE) {
        fprintf(stderr, "We seem to already be registered, deregistering %s!\n",
                m_impl->reason_to_string(cb_data.reason));
        cleanup_callback();
    }

    vpiHandle new_hdl = vpi_register_cb(&cb_data);

    if (!new_hdl) {
        LOG_ERROR(
            "VPI: Unable to register a callback handle for VPI type %s(%d)",
            m_impl->reason_to_string(cb_data.reason), cb_data.reason);
        check_vpi_error();
        return -1;

    } else {
        m_state = GPI_PRIMED;
    }

    m_obj_hdl = new_hdl;

    return 0;
}

int VpiCbHdl::cleanup_callback() {
    if (m_state == GPI_FREE) return 0;

    /* If the one-time callback has not come back then
     * remove it, it is has then free it. The remove is done
     * internally */

    if (m_state == GPI_PRIMED) {
        if (!m_obj_hdl) {
            LOG_ERROR("VPI: passed a NULL pointer");
            return -1;
        }

        if (!(vpi_remove_cb(get_handle<vpiHandle>()))) {
            LOG_ERROR("VPI: unable to remove callback");
            return -1;
        }

        check_vpi_error();
    } else {
#ifndef MODELSIM
        /* This is disabled for now, causes a small leak going to put back in */
        if (!(vpi_free_object(get_handle<vpiHandle>()))) {
            LOG_ERROR("VPI: unable to free handle");
            return -1;
        }
#endif
    }

    m_obj_hdl = NULL;
    m_state = GPI_FREE;

    return 0;
}

int VpiArrayObjHdl::initialise(std::string &name, std::string &fq_name) {
    vpiHandle hdl = GpiObjHdl::get_handle<vpiHandle>();

    m_indexable = true;

    int range_idx = 0;

    /* Need to determine if this is a pseudo-handle to be able to select the
     * correct range */
    std::string hdl_name = vpi_get_str(vpiName, hdl);

    /* Removing the hdl_name from the name will leave the pseudo-indices */
    if (hdl_name.length() < name.length()) {
        std::string idx_str = name.substr(hdl_name.length());

        while (idx_str.length() > 0) {
            std::size_t found = idx_str.find_first_of("]");

            if (found != std::string::npos) {
                ++range_idx;
                idx_str = idx_str.substr(found + 1);
            } else {
                break;
            }
        }
    }

    /* After determining the range_idx, get the range and set the limits */
    vpiHandle iter = vpi_iterate(vpiRange, hdl);

    s_vpi_value val;
    val.format = vpiIntVal;

    if (iter != NULL) {
        vpiHandle rangeHdl;
        int idx = 0;

        while ((rangeHdl = vpi_scan(iter)) != NULL) {
            if (idx == range_idx) {
                break;
            }
            ++idx;
        }

        if (rangeHdl == NULL) {
            LOG_ERROR("Unable to get range for indexable object");
            return -1;
        } else {
            vpi_free_object(iter);  // Need to free iterator since exited early

            vpi_get_value(vpi_handle(vpiLeftRange, rangeHdl), &val);
            check_vpi_error();
            m_range_left = val.value.integer;

            vpi_get_value(vpi_handle(vpiRightRange, rangeHdl), &val);
            check_vpi_error();
            m_range_right = val.value.integer;
        }
    } else if (range_idx == 0) {
        vpi_get_value(vpi_handle(vpiLeftRange, hdl), &val);
        check_vpi_error();
        m_range_left = val.value.integer;

        vpi_get_value(vpi_handle(vpiRightRange, hdl), &val);
        check_vpi_error();
        m_range_right = val.value.integer;
    } else {
        LOG_ERROR("Unable to get range for indexable object");
        return -1;
    }

    /* vpiSize will return a size that is incorrect for multi-dimensional arrays
     * so use the range to calculate the m_num_elems.
     *
     *    For example:
     *       wire [7:0] sig_t4 [0:3][7:4]
     *
     *    The size of "sig_t4" will be reported as 16 through the vpi interface.
     */
    if (m_range_left > m_range_right) {
        m_num_elems = m_range_left - m_range_right + 1;
    } else {
        m_num_elems = m_range_right - m_range_left + 1;
    }

    return GpiObjHdl::initialise(name, fq_name);
}

int VpiObjHdl::initialise(std::string &name, std::string &fq_name) {
    char *str;
    vpiHandle hdl = GpiObjHdl::get_handle<vpiHandle>();
    str = vpi_get_str(vpiDefName, hdl);
    if (str != NULL) m_definition_name = str;
    str = vpi_get_str(vpiDefFile, hdl);
    if (str != NULL) m_definition_file = str;

    return GpiObjHdl::initialise(name, fq_name);
}

int VpiSignalObjHdl::initialise(std::string &name, std::string &fq_name) {
    int32_t type = vpi_get(vpiType, GpiObjHdl::get_handle<vpiHandle>());
    if ((vpiIntVar == type) || (vpiIntegerVar == type) ||
        (vpiIntegerNet == type) || (vpiRealNet == type)) {
        m_num_elems = 1;
    } else {
        m_num_elems = vpi_get(vpiSize, GpiObjHdl::get_handle<vpiHandle>());

        if (GpiObjHdl::get_type() == GPI_STRING) {
            m_indexable = false;  // Don't want to iterate over indices
            m_range_left = 0;
            m_range_right = m_num_elems - 1;
        } else if (GpiObjHdl::get_type() == GPI_REGISTER ||
                   GpiObjHdl::get_type() == GPI_NET) {
            vpiHandle hdl = GpiObjHdl::get_handle<vpiHandle>();

            m_indexable = vpi_get(vpiVector, hdl);

            if (m_indexable) {
                s_vpi_value val;
                vpiHandle iter;

                val.format = vpiIntVal;

                iter = vpi_iterate(vpiRange, hdl);

                /* Only ever need the first "range" */
                if (iter != NULL) {
                    vpiHandle rangeHdl = vpi_scan(iter);

                    vpi_free_object(iter);

                    if (rangeHdl != NULL) {
                        vpi_get_value(vpi_handle(vpiLeftRange, rangeHdl), &val);
                        check_vpi_error();
                        m_range_left = val.value.integer;

                        vpi_get_value(vpi_handle(vpiRightRange, rangeHdl),
                                      &val);
                        check_vpi_error();
                        m_range_right = val.value.integer;
                    } else {
                        LOG_ERROR("Unable to get range for indexable object");
                        return -1;
                    }
                } else {
                    vpi_get_value(vpi_handle(vpiLeftRange, hdl), &val);
                    check_vpi_error();
                    m_range_left = val.value.integer;

                    vpi_get_value(vpi_handle(vpiRightRange, hdl), &val);
                    check_vpi_error();
                    m_range_right = val.value.integer;
                }

                LOG_DEBUG(
                    "VPI: Indexable object initialized with range [%d:%d] and "
                    "length >%d<",
                    m_range_left, m_range_right, m_num_elems);
            }
        }
    }
    LOG_DEBUG("VPI: %s initialized with %d elements", name.c_str(),
              m_num_elems);
    return GpiObjHdl::initialise(name, fq_name);
}

const char *VpiSignalObjHdl::get_signal_value_binstr() {
    s_vpi_value value_s = {vpiBinStrVal, {NULL}};

    vpi_get_value(GpiObjHdl::get_handle<vpiHandle>(), &value_s);
    check_vpi_error();

    return value_s.value.str;
}

const char *VpiSignalObjHdl::get_signal_value_str() {
    s_vpi_value value_s = {vpiStringVal, {NULL}};

    vpi_get_value(GpiObjHdl::get_handle<vpiHandle>(), &value_s);
    check_vpi_error();

    return value_s.value.str;
}

double VpiSignalObjHdl::get_signal_value_real() {
    s_vpi_value value_s = {vpiRealVal, {NULL}};

    vpi_get_value(GpiObjHdl::get_handle<vpiHandle>(), &value_s);
    check_vpi_error();

    return value_s.value.real;
}

long VpiSignalObjHdl::get_signal_value_long() {
    s_vpi_value value_s = {vpiIntVal, {NULL}};

    vpi_get_value(GpiObjHdl::get_handle<vpiHandle>(), &value_s);
    check_vpi_error();

    return value_s.value.integer;
}

// Value related functions
int VpiSignalObjHdl::set_signal_value(int32_t value, gpi_set_action_t action) {
    s_vpi_value value_s;

    value_s.value.integer = static_cast<PLI_INT32>(value);
    value_s.format = vpiIntVal;

    return set_signal_value(value_s, action);
}

int VpiSignalObjHdl::set_signal_value(double value, gpi_set_action_t action) {
    s_vpi_value value_s;

    value_s.value.real = value;
    value_s.format = vpiRealVal;

    return set_signal_value(value_s, action);
}

int VpiSignalObjHdl::set_signal_value_binstr(std::string &value,
                                             gpi_set_action_t action) {
    s_vpi_value value_s;

    std::vector<char> writable(value.begin(), value.end());
    writable.push_back('\0');

    value_s.value.str = &writable[0];
    value_s.format = vpiBinStrVal;

    return set_signal_value(value_s, action);
}

int VpiSignalObjHdl::set_signal_value_str(std::string &value,
                                          gpi_set_action_t action) {
    s_vpi_value value_s;

    std::vector<char> writable(value.begin(), value.end());
    writable.push_back('\0');

    value_s.value.str = &writable[0];
    value_s.format = vpiStringVal;

    return set_signal_value(value_s, action);
}

int VpiSignalObjHdl::set_signal_value(s_vpi_value value_s,
                                      gpi_set_action_t action) {
    PLI_INT32 vpi_put_flag = -1;
    s_vpi_time vpi_time_s;

    vpi_time_s.type = vpiSimTime;
    vpi_time_s.high = 0;
    vpi_time_s.low = 0;

    switch (action) {
        case GPI_DEPOSIT:
            if (vpiStringVar ==
                vpi_get(vpiType, GpiObjHdl::get_handle<vpiHandle>())) {
                // assigning to a vpiStringVar only seems to work with
                // vpiNoDelay
                vpi_put_flag = vpiNoDelay;
            } else {
                // Use Inertial delay to schedule an event, thus behaving like a
                // verilog testbench
                vpi_put_flag = vpiInertialDelay;
            }
            break;
        case GPI_FORCE:
            vpi_put_flag = vpiForceFlag;
            break;
        case GPI_RELEASE:
            // Best to pass its current value to the sim when releasing
            vpi_get_value(GpiObjHdl::get_handle<vpiHandle>(), &value_s);
            vpi_put_flag = vpiReleaseFlag;
            break;
        default:
            assert(0);
    }

    if (vpi_put_flag == vpiNoDelay) {
        vpi_put_value(GpiObjHdl::get_handle<vpiHandle>(), &value_s, NULL,
                      vpiNoDelay);
    } else {
        vpi_put_value(GpiObjHdl::get_handle<vpiHandle>(), &value_s, &vpi_time_s,
                      vpi_put_flag);
    }

    check_vpi_error();

    return 0;
}

GpiCbHdl *VpiSignalObjHdl::value_change_cb(int edge) {
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

VpiValueCbHdl::VpiValueCbHdl(GpiImplInterface *impl, VpiSignalObjHdl *sig,
                             int edge)
    : GpiCbHdl(impl), VpiCbHdl(impl), GpiValueCbHdl(impl, sig, edge) {
    vpi_time.type = vpiSuppressTime;
    m_vpi_value.format = vpiIntVal;

    cb_data.reason = cbValueChange;
    cb_data.time = &vpi_time;
    cb_data.value = &m_vpi_value;
    cb_data.obj = m_signal->get_handle<vpiHandle>();
}

int VpiValueCbHdl::cleanup_callback() {
    if (m_state == GPI_FREE) return 0;

    /* This is a recurring callback so just remove when
     * not wanted */
    if (!(vpi_remove_cb(get_handle<vpiHandle>()))) {
        LOG_ERROR("VPI: unable to remove callback");
        return -1;
    }

    m_obj_hdl = NULL;
    m_state = GPI_FREE;
    return 0;
}

VpiStartupCbHdl::VpiStartupCbHdl(GpiImplInterface *impl)
    : GpiCbHdl(impl), VpiCbHdl(impl) {
#ifndef IUS
    cb_data.reason = cbStartOfSimulation;
#else
    vpi_time.high = (uint32_t)(0);
    vpi_time.low = (uint32_t)(0);
    vpi_time.type = vpiSimTime;
    cb_data.reason = cbAfterDelay;
#endif
}

int VpiStartupCbHdl::run_callback() {
    s_vpi_vlog_info info;

    if (!vpi_get_vlog_info(&info)) {
        LOG_WARN("Unable to get argv and argc from simulator");
        info.argc = 0;
        info.argv = nullptr;
    }

    gpi_embed_init(info.argc, info.argv);

    return 0;
}

VpiShutdownCbHdl::VpiShutdownCbHdl(GpiImplInterface *impl)
    : GpiCbHdl(impl), VpiCbHdl(impl) {
    cb_data.reason = cbEndOfSimulation;
}

int VpiShutdownCbHdl::run_callback() {
    gpi_embed_end();
    return 0;
}

VpiTimedCbHdl::VpiTimedCbHdl(GpiImplInterface *impl, uint64_t time)
    : GpiCbHdl(impl), VpiCbHdl(impl) {
    vpi_time.high = (uint32_t)(time >> 32);
    vpi_time.low = (uint32_t)(time);
    vpi_time.type = vpiSimTime;

    cb_data.reason = cbAfterDelay;
}

int VpiTimedCbHdl::cleanup_callback() {
    switch (m_state) {
        case GPI_PRIMED:
            /* Issue #188: Work around for modelsim that is harmless to others
               too, we tag the time as delete, let it fire then do not pass up
               */
            LOG_DEBUG("Not removing PRIMED timer %d", vpi_time.low);
            m_state = GPI_DELETE;
            return 0;
        case GPI_DELETE:
            LOG_DEBUG("Removing DELETE timer %d", vpi_time.low);
        default:
            break;
    }
    VpiCbHdl::cleanup_callback();
    /* Return one so we delete this object */
    return 1;
}

VpiReadwriteCbHdl::VpiReadwriteCbHdl(GpiImplInterface *impl)
    : GpiCbHdl(impl), VpiCbHdl(impl) {
    cb_data.reason = cbReadWriteSynch;
}

VpiReadOnlyCbHdl::VpiReadOnlyCbHdl(GpiImplInterface *impl)
    : GpiCbHdl(impl), VpiCbHdl(impl) {
    cb_data.reason = cbReadOnlySynch;
}

VpiNextPhaseCbHdl::VpiNextPhaseCbHdl(GpiImplInterface *impl)
    : GpiCbHdl(impl), VpiCbHdl(impl) {
    cb_data.reason = cbNextSimTime;
}

decltype(VpiIterator::iterate_over) VpiIterator::iterate_over = [] {
    /* for reused lists */
    std::initializer_list<int32_t> module_options = {
        // vpiModule,            // Aldec SEGV on mixed language
        // vpiModuleArray,       // Aldec SEGV on mixed language
        // vpiIODecl,            // Don't care about these
        vpiNet, vpiNetArray, vpiReg, vpiRegArray, vpiMemory, vpiIntegerVar,
        vpiRealVar, vpiRealNet, vpiStructVar, vpiStructNet, vpiVariables,
        vpiNamedEvent, vpiNamedEventArray, vpiParameter,
        // vpiSpecParam,         // Don't care
        // vpiParamAssign,       // Aldec SEGV on mixed language
        // vpiDefParam,          // Don't care
        vpiPrimitive, vpiPrimitiveArray,
        // vpiContAssign,        // Don't care
        vpiProcess,  // Don't care
        vpiModPath, vpiTchk, vpiAttribute, vpiPort, vpiInternalScope,
        // vpiInterface,         // Aldec SEGV on mixed language
        // vpiInterfaceArray,    // Aldec SEGV on mixed language
    };
    std::initializer_list<int32_t> struct_options = {
        vpiNet,
#ifndef IUS
        vpiNetArray,
#endif
        vpiReg,       vpiRegArray,       vpiMemory,    vpiParameter,
        vpiPrimitive, vpiPrimitiveArray, vpiAttribute, vpiMember,
    };

    return decltype(VpiIterator::iterate_over){
        {vpiModule, module_options},
        {vpiGenScope, module_options},

        {vpiStructVar, struct_options},
        {vpiStructNet, struct_options},

        {vpiNet,
         {
             // vpiContAssign,        // Driver and load handled separately
             // vpiPrimTerm,
             // vpiPathTerm,
             // vpiTchkTerm,
             // vpiDriver,
             // vpiLocalDriver,
             // vpiLoad,
             // vpiLocalLoad,
             vpiNetBit,
         }},
        {vpiNetArray,
         {
             vpiNet,
         }},
        {vpiRegArray,
         {
             vpiReg,
         }},
        {vpiMemory,
         {
             vpiMemoryWord,
         }},
        {vpiPort,
         {
             vpiPortBit,
         }},
        {vpiGate,
         {
             vpiPrimTerm,
             vpiTableEntry,
             vpiUdpDefn,
         }},
    };
}();

VpiIterator::VpiIterator(GpiImplInterface *impl, GpiObjHdl *hdl)
    : GpiIterator(impl, hdl), m_iterator(NULL) {
    vpiHandle iterator;
    vpiHandle vpi_hdl = m_parent->get_handle<vpiHandle>();

    int type = vpi_get(vpiType, vpi_hdl);
    try {
        selected = &iterate_over.at(type);
    } catch (std::out_of_range const &) {
        LOG_WARN("VPI: Implementation does not know how to iterate over %s(%d)",
                 vpi_get_str(vpiType, vpi_hdl), type);
        selected = nullptr;
        return;
    }

    for (one2many = selected->begin(); one2many != selected->end();
         one2many++) {
        /* GPI_GENARRAY are pseudo-regions and all that should be searched for
         * are the sub-regions */
        if (m_parent->get_type() == GPI_GENARRAY &&
            *one2many != vpiInternalScope) {
            LOG_DEBUG(
                "vpi_iterator vpiOneToManyT=%d skipped for GPI_GENARRAY type",
                *one2many);
            continue;
        }

        iterator = vpi_iterate(*one2many, vpi_hdl);

        if (iterator) {
            break;
        }

        LOG_DEBUG("vpi_iterate type=%d returned NULL", *one2many);
    }

    if (NULL == iterator) {
        LOG_DEBUG(
            "vpi_iterate return NULL for all relationships on %s (%d) type:%s",
            vpi_get_str(vpiName, vpi_hdl), type, vpi_get_str(vpiType, vpi_hdl));
        selected = NULL;
        return;
    }

    LOG_DEBUG("Created iterator working from '%s' with type %s(%d)",
              vpi_get_str(vpiFullName, vpi_hdl), vpi_get_str(vpiType, vpi_hdl),
              type);

    m_iterator = iterator;
}

VpiIterator::~VpiIterator() {
    if (m_iterator) vpi_free_object(m_iterator);
}

#define VPI_TYPE_MAX (1000)

GpiIterator::Status VpiSingleIterator::next_handle(std::string &name,
                                                   GpiObjHdl **hdl,
                                                   void **raw_hdl) {
    GpiObjHdl *new_obj;
    vpiHandle obj;

    if (NULL == m_iterator) return GpiIterator::END;

    obj = vpi_scan(m_iterator);
    if (NULL == obj) return GpiIterator::END;

    const char *c_name = vpi_get_str(vpiName, obj);
    if (!c_name) {
        int type = vpi_get(vpiType, obj);

        if (type >= VPI_TYPE_MAX) {
            *raw_hdl = (void *)obj;
            return GpiIterator::NOT_NATIVE_NO_NAME;
        }

        LOG_DEBUG("Unable to get the name for this object of type %d", type);

        return GpiIterator::NATIVE_NO_NAME;
    }

    std::string fq_name = c_name;

    LOG_DEBUG("vpi_scan found '%s = '%s'", name.c_str(), fq_name.c_str());

    VpiImpl *vpi_impl = reinterpret_cast<VpiImpl *>(m_impl);
    new_obj = vpi_impl->create_gpi_obj_from_handle(obj, name, fq_name);
    if (new_obj) {
        *hdl = new_obj;
        return GpiIterator::NATIVE;
    } else
        return GpiIterator::NOT_NATIVE;
}

GpiIterator::Status VpiIterator::next_handle(std::string &name, GpiObjHdl **hdl,
                                             void **raw_hdl) {
    GpiObjHdl *new_obj;
    vpiHandle obj;
    vpiHandle iter_obj = m_parent->get_handle<vpiHandle>();

    if (!selected) return GpiIterator::END;

    gpi_objtype_t obj_type = m_parent->get_type();
    std::string parent_name = m_parent->get_name();

    do {
        obj = NULL;

        if (m_iterator) {
            obj = vpi_scan(m_iterator);

            /* For GPI_GENARRAY, only allow the generate statements through that
             * match the name of the generate block.
             */
            if (obj != NULL && obj_type == GPI_GENARRAY) {
                if (vpi_get(vpiType, obj) == vpiGenScope) {
                    std::string rgn_name = vpi_get_str(vpiName, obj);
                    if (rgn_name.compare(0, parent_name.length(),
                                         parent_name) != 0) {
                        obj = NULL;
                        continue;
                    }
                } else {
                    obj = NULL;
                    continue;
                }
            }

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

        /* GPI_GENARRAY are pseudo-regions and all that should be searched for
         * are the sub-regions */
        if (obj_type == GPI_GENARRAY && *one2many != vpiInternalScope) {
            LOG_DEBUG(
                "vpi_iterator vpiOneToManyT=%d skipped for GPI_GENARRAY type",
                *one2many);
            continue;
        }

        m_iterator = vpi_iterate(*one2many, iter_obj);

    } while (!obj);

    if (NULL == obj) {
        LOG_DEBUG("No more children, all relationships tested");
        return GpiIterator::END;
    }

    /* Simulators vary here. Some will allow the name to be accessed
       across boundary. We can simply return this up and allow
       the object to be created. Others do not. In this case
       we see if the object is in our type range and if not
       return the raw_hdl up */

    const char *c_name = vpi_get_str(vpiName, obj);
    if (!c_name) {
        /* This may be another type */
        int type = vpi_get(vpiType, obj);

        if (type >= VPI_TYPE_MAX) {
            *raw_hdl = (void *)obj;
            return GpiIterator::NOT_NATIVE_NO_NAME;
        }

        LOG_DEBUG("Unable to get the name for this object of type %d", type);

        return GpiIterator::NATIVE_NO_NAME;
    }

    /*
     * If the parent is not a generate loop, then watch for generate handles and
     * create the pseudo-region.
     *
     * NOTE: Taking advantage of the "caching" to only create one pseudo-region
     * object. Otherwise a list would be required and checked while iterating
     */
    if (*one2many == vpiInternalScope && obj_type != GPI_GENARRAY &&
        vpi_get(vpiType, obj) == vpiGenScope) {
        std::string idx_str = c_name;
        std::size_t found = idx_str.rfind("[");

        if (found != std::string::npos && found != 0) {
            name = idx_str.substr(0, found);
            obj = m_parent->get_handle<vpiHandle>();
        } else {
            name = c_name;
        }
    } else {
        name = c_name;
    }

    /* We try and create a handle internally, if this is not possible we
       return and GPI will try other implementations with the name
       */

    std::string fq_name = m_parent->get_fullname();

    if (obj_type == GPI_GENARRAY) {
        std::size_t found = name.rfind("[");

        if (found != std::string::npos) {
            fq_name += name.substr(found);
        } else {
            LOG_WARN("Unhandled Sub-Element Format - %s", name.c_str());
            fq_name += "." + name;
        }
    } else if (obj_type == GPI_STRUCTURE) {
        std::size_t found = name.rfind(".");

        if (found != std::string::npos) {
            fq_name += name.substr(found);
            name = name.substr(found + 1);
        } else {
            LOG_WARN("Unhandled Sub-Element Format - %s", name.c_str());
            fq_name += "." + name;
        }
    } else {
        fq_name += "." + name;
    }

    LOG_DEBUG("vpi_scan found '%s'", fq_name.c_str());
    VpiImpl *vpi_impl = reinterpret_cast<VpiImpl *>(m_impl);
    new_obj = vpi_impl->create_gpi_obj_from_handle(obj, name, fq_name);
    if (new_obj) {
        *hdl = new_obj;
        return GpiIterator::NATIVE;
    } else
        return GpiIterator::NOT_NATIVE;
}
