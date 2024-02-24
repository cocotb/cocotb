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

int VpiSignalObjHdl::initialise(const std::string &name,
                                const std::string &fq_name) {
    int32_t type = vpi_get(vpiType, GpiObjHdl::get_handle<vpiHandle>());
    if ((vpiIntVar == type) || (vpiIntegerVar == type) ||
        (vpiIntegerNet == type) || (vpiRealNet == type)) {
        m_num_elems = 1;
    } else {
        m_num_elems = vpi_get(vpiSize, GpiObjHdl::get_handle<vpiHandle>());

        if (GpiObjHdl::get_type() == GPI_STRING || type == vpiConstant ||
            type == vpiParameter) {
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
                    vpiHandle leftRange = vpi_handle(vpiLeftRange, hdl);
                    check_vpi_error();
                    vpiHandle rightRange = vpi_handle(vpiRightRange, hdl);
                    check_vpi_error();

                    if (leftRange != NULL and rightRange != NULL) {
                        vpi_get_value(leftRange, &val);
                        m_range_left = val.value.integer;

                        vpi_get_value(rightRange, &val);
                        m_range_right = val.value.integer;
                    } else {
                        LOG_WARN(
                            "VPI: Cannot discover range bounds, guessing based "
                            "on elements");
                        m_range_left = 0;
                        m_range_right = m_num_elems - 1;
                    }
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

GpiCbHdl *VpiSignalObjHdl::register_value_change_callback(
    int edge, int (*function)(void *), void *cb_data) {
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

    cb->set_user_data(function, cb_data);
    if (cb->arm_callback()) {
        return NULL;
    }

    return cb;
}
