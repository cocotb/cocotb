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
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 *AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 *IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
 * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 ******************************************************************************/

#include <assert.h>

#include <cinttypes>  // fixed-size int types and format strings
#include <limits>     // numeric_limits
#include <stdexcept>

#include "VhpiImpl.h"

namespace {
using bufSize_type = decltype(vhpiValueT::bufSize);
}

extern "C" void handle_vhpi_callback(const vhpiCbDataT *cb_data);

VhpiArrayObjHdl::~VhpiArrayObjHdl() {
    LOG_DEBUG("VHPI: Releasing VhpiArrayObjHdl handle at %p",
              (void *)get_handle<vhpiHandleT>());
    if (vhpi_release_handle(get_handle<vhpiHandleT>())) check_vhpi_error();
}

VhpiObjHdl::~VhpiObjHdl() {
    /* Don't release handles for pseudo-regions, as they borrow the handle of
     * the containing region */
    if (m_type != GPI_GENARRAY) {
        LOG_DEBUG("VHPI: Releasing VhpiObjHdl handle at %p",
                  (void *)get_handle<vhpiHandleT>());
        if (vhpi_release_handle(get_handle<vhpiHandleT>())) check_vhpi_error();
    }
}

VhpiSignalObjHdl::~VhpiSignalObjHdl() {
    switch (m_value.format) {
        case vhpiIntVecVal:
        case vhpiEnumVecVal:
        case vhpiLogicVecVal:
            delete[] m_value.value.enumvs;
        default:
            break;
    }

    if (m_binvalue.value.str) delete[] m_binvalue.value.str;

    LOG_DEBUG("VHPI: Releasing VhpiSignalObjHdl handle at %p",
              (void *)get_handle<vhpiHandleT>());
    if (vhpi_release_handle(get_handle<vhpiHandleT>())) check_vhpi_error();
}

bool get_range(vhpiHandleT hdl, vhpiIntT dim, int *left, int *right) {
#ifdef IUS
    /* IUS/Xcelium does not appear to set the vhpiIsUnconstrainedP property. IUS
     * Docs say will return -1 if unconstrained, but with vhpiIntT being
     * unsigned, the value returned is below.
     */
    const vhpiIntT UNCONSTRAINED = 2147483647;
#endif

    bool error = true;

    vhpiHandleT base_hdl = vhpi_handle(vhpiBaseType, hdl);

    if (base_hdl == NULL) {
        vhpiHandleT st_hdl = vhpi_handle(vhpiSubtype, hdl);

        if (st_hdl != NULL) {
            base_hdl = vhpi_handle(vhpiBaseType, st_hdl);
            vhpi_release_handle(st_hdl);
        }
    }

    if (base_hdl != NULL) {
        vhpiHandleT it = vhpi_iterator(vhpiConstraints, base_hdl);
        vhpiIntT curr_idx = 0;

        if (it != NULL) {
            vhpiHandleT constraint;
            while ((constraint = vhpi_scan(it)) != NULL) {
                if (curr_idx == dim) {
                    vhpi_release_handle(it);
                    vhpiIntT l_rng = vhpi_get(vhpiLeftBoundP, constraint);
                    vhpiIntT r_rng = vhpi_get(vhpiRightBoundP, constraint);
#ifdef IUS
                    if (l_rng != UNCONSTRAINED && r_rng != UNCONSTRAINED) {
#else
                    if (vhpi_get(vhpiIsUnconstrainedP, constraint)) {
#endif
                        error = false;
                        *left = static_cast<int>(l_rng);
                        *right = static_cast<int>(r_rng);
                    }
                    break;
                }
                ++curr_idx;
            }
        }
        vhpi_release_handle(base_hdl);
    }

    if (error) {
        vhpiHandleT sub_type_hdl = vhpi_handle(vhpiSubtype, hdl);

        if (sub_type_hdl != NULL) {
            vhpiHandleT it = vhpi_iterator(vhpiConstraints, sub_type_hdl);
            vhpiIntT curr_idx = 0;

            if (it != NULL) {
                vhpiHandleT constraint;
                while ((constraint = vhpi_scan(it)) != NULL) {
                    if (curr_idx == dim) {
                        vhpi_release_handle(it);

                        /* IUS/Xcelium only sets the vhpiIsUnconstrainedP
                         * incorrectly on the base type */
                        if (!vhpi_get(vhpiIsUnconstrainedP, constraint)) {
                            error = false;
                            *left = static_cast<int>(
                                vhpi_get(vhpiLeftBoundP, constraint));
                            *right = static_cast<int>(
                                vhpi_get(vhpiRightBoundP, constraint));
                        }
                        break;
                    }
                    ++curr_idx;
                }
            }
            vhpi_release_handle(sub_type_hdl);
        }
    }

    return error;
}

vhpiPutValueModeT map_put_value_mode(gpi_set_action_t action) {
    vhpiPutValueModeT put_value_mode = vhpiDeposit;
    switch (action) {
        case GPI_DEPOSIT:
            put_value_mode = vhpiDepositPropagate;
            break;
        case GPI_FORCE:
            put_value_mode = vhpiForcePropagate;
            break;
        case GPI_RELEASE:
            put_value_mode = vhpiRelease;
            break;
        default:
            assert(0);
    }
    return put_value_mode;
}

int VhpiArrayObjHdl::initialise(std::string &name, std::string &fq_name) {
    vhpiHandleT handle = GpiObjHdl::get_handle<vhpiHandleT>();

    m_indexable = true;

    vhpiHandleT type = vhpi_handle(vhpiBaseType, handle);

    if (type == NULL) {
        vhpiHandleT st_hdl = vhpi_handle(vhpiSubtype, handle);

        if (st_hdl != NULL) {
            type = vhpi_handle(vhpiBaseType, st_hdl);
            vhpi_release_handle(st_hdl);
        }
    }

    if (NULL == type) {
        LOG_ERROR("VHPI: Unable to get vhpiBaseType for %s", fq_name.c_str());
        return -1;
    }

    vhpiIntT num_dim = vhpi_get(vhpiNumDimensionsP, type);
    vhpiIntT dim_idx = 0;

    /* Need to determine which dimension constraint is needed */
    if (num_dim > 1) {
        std::string hdl_name = vhpi_get_str(vhpiCaseNameP, handle);

        if (hdl_name.length() < name.length()) {
            std::string pseudo_idx = name.substr(hdl_name.length());

            while (pseudo_idx.length() > 0) {
                std::size_t found = pseudo_idx.find_first_of(")");

                if (found != std::string::npos) {
                    ++dim_idx;
                    pseudo_idx = pseudo_idx.substr(found + 1);
                } else {
                    break;
                }
            }
        }
    }

    bool error = get_range(handle, dim_idx, &m_range_left, &m_range_right);

    if (error) {
        LOG_ERROR(
            "VHPI: Unable to obtain constraints for an indexable object %s.",
            fq_name.c_str());
        return -1;
    }

    if (m_range_left > m_range_right) {
        m_num_elems = m_range_left - m_range_right + 1;
    } else {
        m_num_elems = m_range_right - m_range_left + 1;
    }

    return GpiObjHdl::initialise(name, fq_name);
}

int VhpiObjHdl::initialise(std::string &name, std::string &fq_name) {
    vhpiHandleT handle = GpiObjHdl::get_handle<vhpiHandleT>();
    if (handle != NULL) {
        vhpiHandleT du_handle = vhpi_handle(vhpiDesignUnit, handle);
        if (du_handle != NULL) {
            vhpiHandleT pu_handle = vhpi_handle(vhpiPrimaryUnit, du_handle);
            if (pu_handle != NULL) {
                const char *str;
                str = vhpi_get_str(vhpiNameP, pu_handle);
                if (str != NULL) m_definition_name = str;

                str = vhpi_get_str(vhpiFileNameP, pu_handle);
                if (str != NULL) m_definition_file = str;
            }
        }
    }

    return GpiObjHdl::initialise(name, fq_name);
}

int VhpiSignalObjHdl::initialise(std::string &name, std::string &fq_name) {
    // Determine the type of object, either scalar or vector
    m_value.format = vhpiObjTypeVal;
    m_value.bufSize = 0;
    m_value.value.str = NULL;
    m_value.numElems = 0;
    /* We also alloc a second value member for use with read string operations
     */
    m_binvalue.format = vhpiBinStrVal;
    m_binvalue.bufSize = 0;
    m_binvalue.numElems = 0;
    m_binvalue.value.str = NULL;

    vhpiHandleT handle = GpiObjHdl::get_handle<vhpiHandleT>();

    if (0 > vhpi_get_value(get_handle<vhpiHandleT>(), &m_value)) {
        LOG_ERROR("VHPI: vhpi_get_value failed for %s (%s)", fq_name.c_str(),
                  vhpi_get_str(vhpiKindStrP, handle));
        return -1;
    }

    LOG_DEBUG(
        "VHPI: Found %s of format type %s (%d) format object with %d elems "
        "buffsize %d size %d",
        name.c_str(),
        ((VhpiImpl *)GpiObjHdl::m_impl)->format_to_string(m_value.format),
        m_value.format, m_value.numElems, m_value.bufSize,
        vhpi_get(vhpiSizeP, handle));

    // Default - overridden below in certain special cases
    m_num_elems = m_value.numElems;

    switch (m_value.format) {
        case vhpiIntVal:
        case vhpiEnumVal:
        case vhpiRealVal:
        case vhpiCharVal: {
            break;
        }

        case vhpiStrVal: {
            m_indexable = true;
            m_num_elems = static_cast<int>(vhpi_get(vhpiSizeP, handle));
            int bufSize = m_num_elems * static_cast<int>(sizeof(vhpiCharT)) + 1;
            m_value.bufSize = static_cast<bufSize_type>(bufSize);
            m_value.value.str = new vhpiCharT[bufSize];
            m_value.numElems = m_num_elems;
            LOG_DEBUG("VHPI: Overriding num_elems to %d", m_num_elems);
            break;
        }

        default: {
            LOG_ERROR(
                "VHPI: Unable to determine property for %s (%d) format object",
                ((VhpiImpl *)GpiObjHdl::m_impl)
                    ->format_to_string(m_value.format),
                m_value.format);
            return -1;
        }
    }

    if (m_indexable && get_range(handle, 0, &m_range_left, &m_range_right)) {
        m_indexable = false;
    }

    if (m_num_elems) {
        int bufSize = m_num_elems * static_cast<int>(sizeof(vhpiCharT)) + 1;
        m_binvalue.bufSize = static_cast<bufSize_type>(bufSize);
        m_binvalue.value.str = new vhpiCharT[bufSize];
    }

    return GpiObjHdl::initialise(name, fq_name);
}

int VhpiLogicSignalObjHdl::initialise(std::string &name, std::string &fq_name) {
    // Determine the type of object, either scalar or vector
    m_value.format = vhpiLogicVal;
    m_value.bufSize = 0;
    m_value.value.str = NULL;
    m_value.numElems = 0;
    /* We also alloc a second value member for use with read string operations
     */
    m_binvalue.format = vhpiBinStrVal;
    m_binvalue.bufSize = 0;
    m_binvalue.numElems = 0;
    m_binvalue.value.str = NULL;

    vhpiHandleT handle = GpiObjHdl::get_handle<vhpiHandleT>();
    vhpiHandleT base_hdl = vhpi_handle(vhpiBaseType, handle);

    if (base_hdl == NULL) {
        vhpiHandleT st_hdl = vhpi_handle(vhpiSubtype, handle);

        if (st_hdl != NULL) {
            base_hdl = vhpi_handle(vhpiBaseType, st_hdl);
            vhpi_release_handle(st_hdl);
        }
    }

    vhpiHandleT query_hdl = (base_hdl != NULL) ? base_hdl : handle;

    m_num_elems = static_cast<int>(vhpi_get(vhpiSizeP, handle));

    if (m_num_elems == 0) {
        LOG_DEBUG("VHPI: Null vector... Delete object")
        return -1;
    }

    if (vhpi_get(vhpiKindP, query_hdl) == vhpiArrayTypeDeclK) {
        m_indexable = true;
        m_value.format = vhpiLogicVecVal;
        int bufSize = m_num_elems * static_cast<int>(sizeof(vhpiEnumT));
        m_value.bufSize = static_cast<bufSize_type>(bufSize);
        m_value.value.enumvs = new vhpiEnumT[bufSize];
    }

    if (m_indexable && get_range(handle, 0, &m_range_left, &m_range_right)) {
        m_indexable = false;
    }

    if (m_num_elems) {
        int bufSize = m_num_elems * static_cast<int>(sizeof(vhpiCharT)) + 1;
        m_binvalue.bufSize = static_cast<bufSize_type>(bufSize);
        m_binvalue.value.str = new vhpiCharT[bufSize];
    }

    return GpiObjHdl::initialise(name, fq_name);
}

VhpiCbHdl::VhpiCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl) {
    cb_data.reason = 0;
    cb_data.cb_rtn = handle_vhpi_callback;
    cb_data.obj = NULL;
    cb_data.time = NULL;
    cb_data.value = NULL;
    cb_data.user_data = (char *)this;

    vhpi_time.high = 0;
    vhpi_time.low = 0;
}

int VhpiCbHdl::cleanup_callback() {
    /* For non timer callbacks we disable rather than remove */
    int ret = 0;
    if (m_state == GPI_FREE) return 0;

    vhpiStateT cbState =
        (vhpiStateT)vhpi_get(vhpiStateP, get_handle<vhpiHandleT>());
    if (vhpiEnable == cbState) {
        ret = vhpi_disable_cb(get_handle<vhpiHandleT>());
        m_state = GPI_FREE;
    }

    if (ret) check_vhpi_error();

    return 0;
}

int VhpiCbHdl::arm_callback() {
    int ret = 0;
    vhpiStateT cbState;

    if (m_state == GPI_PRIMED) return 0;

    /* Do we already have a handle? If so and it is disabled then
       just re-enable it. */

    if (get_handle<vhpiHandleT>()) {
        cbState = (vhpiStateT)vhpi_get(vhpiStateP, get_handle<vhpiHandleT>());
        if (vhpiDisable == cbState) {
            if (vhpi_enable_cb(get_handle<vhpiHandleT>())) {
                check_vhpi_error();
                goto error;
            }
        }
    } else {
        vhpiHandleT new_hdl = vhpi_register_cb(&cb_data, vhpiReturnCb);

        if (!new_hdl) {
            check_vhpi_error();
            LOG_ERROR(
                "VHPI: Unable to register a callback handle for VHPI type "
                "%s(%d)",
                m_impl->reason_to_string(cb_data.reason), cb_data.reason);
            goto error;
        }

        // don't cast to vhpiStateT immediately because vhpiUndefined is not in
        // the enum
        vhpiIntT cbState_raw = vhpi_get(vhpiStateP, new_hdl);
        if ((vhpiIntT)vhpiUndefined == cbState_raw) {
            LOG_ERROR(
                "VHPI: Registered callback isn't enabled! Got "
                "vhpiStateP=vhpiUndefined(%d)",
                vhpiUndefined);
            goto error;
        } else if (vhpiEnable != (vhpiStateT)cbState_raw) {
            LOG_ERROR(
                "VHPI: Registered callback isn't enabled! Got vhpiStateP=%d",
                (vhpiStateT)cbState_raw);
            goto error;
        }

        m_obj_hdl = new_hdl;
    }
    m_state = GPI_PRIMED;

    return ret;

error:
    m_state = GPI_FREE;
    return -1;
}

// Value related functions
vhpiEnumT VhpiSignalObjHdl::chr2vhpi(const char value) {
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
int VhpiLogicSignalObjHdl::set_signal_value(int32_t value,
                                            gpi_set_action_t action) {
    switch (m_value.format) {
        case vhpiEnumVal:
        case vhpiLogicVal: {
            m_value.value.enumv = value ? vhpi1 : vhpi0;
            break;
        }

        case vhpiEnumVecVal:
        case vhpiLogicVecVal: {
            int i;
            for (i = 0; i < m_num_elems; i++)
                m_value.value.enumvs[m_num_elems - i - 1] =
                    value & (1 << i) ? vhpi1 : vhpi0;

            m_value.numElems = m_num_elems;
            break;
        }

        default: {
            LOG_ERROR(
                "VHPI: Unable to set a std_logic signal with a raw value");
            return -1;
        }
    }

    if (vhpi_put_value(GpiObjHdl::get_handle<vhpiHandleT>(), &m_value,
                       map_put_value_mode(action))) {
        check_vhpi_error();
        return -1;
    }

    return 0;
}

int VhpiLogicSignalObjHdl::set_signal_value_binstr(std::string &value,
                                                   gpi_set_action_t action) {
    switch (m_value.format) {
        case vhpiEnumVal:
        case vhpiLogicVal: {
            m_value.value.enumv = chr2vhpi(value.c_str()[0]);
            break;
        }

        case vhpiEnumVecVal:
        case vhpiLogicVecVal: {
            if ((int)value.length() != m_num_elems) {
                LOG_ERROR(
                    "VHPI: Unable to set logic vector due to the string having "
                    "incorrect length.  Length of %d needs to be %d",
                    value.length(), m_num_elems);
                return -1;
            }

            m_value.numElems = m_num_elems;

            std::string::iterator iter;

            int i = 0;
            for (iter = value.begin();
                 (iter != value.end()) && (i < m_num_elems); iter++, i++) {
                m_value.value.enumvs[i] = chr2vhpi(*iter);
            }

            break;
        }

        default: {
            LOG_ERROR(
                "VHPI: Unable to set a std_logic signal with a raw value");
            return -1;
        }
    }

    if (vhpi_put_value(GpiObjHdl::get_handle<vhpiHandleT>(), &m_value,
                       map_put_value_mode(action))) {
        check_vhpi_error();
        return -1;
    }

    return 0;
}

// Value related functions
int VhpiSignalObjHdl::set_signal_value(int32_t value, gpi_set_action_t action) {
    switch (m_value.format) {
        case vhpiEnumVecVal:
        case vhpiLogicVecVal: {
            int i;
            for (i = 0; i < m_num_elems; i++)
                m_value.value.enumvs[m_num_elems - i - 1] =
                    value & (1 << i) ? vhpi1 : vhpi0;

            // Since we may not get the numElems correctly from the sim and have
            // to infer it we also need to set it here as well each time.

            m_value.numElems = m_num_elems;
            break;
        }

        case vhpiLogicVal:
        case vhpiEnumVal: {
            m_value.value.enumv = static_cast<vhpiEnumT>(value);
            break;
        }

        case vhpiIntVal: {
            m_value.value.intg = static_cast<vhpiIntT>(value);
            break;
        }

        case vhpiCharVal: {
            using CharLimits = std::numeric_limits<vhpiCharT>;
            if ((value > CharLimits::max()) || (value < CharLimits::min())) {
                LOG_ERROR("VHPI: Data loss detected");
                return -1;
            }
            m_value.value.ch = static_cast<vhpiCharT>(value);
            break;
        }

        default: {
            LOG_ERROR("VHPI: Unable to handle this format type %s",
                      ((VhpiImpl *)GpiObjHdl::m_impl)
                          ->format_to_string(m_value.format));
            return -1;
        }
    }
    if (vhpi_put_value(GpiObjHdl::get_handle<vhpiHandleT>(), &m_value,
                       map_put_value_mode(action))) {
        check_vhpi_error();
        return -1;
    }

    return 0;
}

int VhpiSignalObjHdl::set_signal_value(double value, gpi_set_action_t action) {
    switch (m_value.format) {
        case vhpiRealVal:
            m_value.numElems = 1;
            m_value.bufSize = sizeof(value);
            m_value.value.real = value;
            break;

        default: {
            LOG_ERROR("VHPI: Unable to set a Real handle with format type %s",
                      ((VhpiImpl *)GpiObjHdl::m_impl)
                          ->format_to_string(m_value.format));
            return -1;
        }
    }

    if (vhpi_put_value(GpiObjHdl::get_handle<vhpiHandleT>(), &m_value,
                       map_put_value_mode(action))) {
        check_vhpi_error();
        return -1;
    }

    return 0;
}

int VhpiSignalObjHdl::set_signal_value_binstr(std::string &value,
                                              gpi_set_action_t action) {
    switch (m_value.format) {
        case vhpiEnumVal:
        case vhpiLogicVal: {
            m_value.value.enumv = chr2vhpi(value.c_str()[0]);
            break;
        }

        case vhpiEnumVecVal:
        case vhpiLogicVecVal: {
            if ((int)value.length() != m_num_elems) {
                LOG_ERROR(
                    "VHPI: Unable to set logic vector due to the string having "
                    "incorrect length.  Length of %d needs to be %d",
                    value.length(), m_num_elems);
                return -1;
            }

            m_value.numElems = m_num_elems;

            std::string::iterator iter;

            int i = 0;
            for (iter = value.begin();
                 (iter != value.end()) && (i < m_num_elems); iter++, i++) {
                m_value.value.enumvs[i] = chr2vhpi(*iter);
            }

            break;
        }

        default: {
            LOG_ERROR("VHPI: Unable to handle this format type: %s",
                      ((VhpiImpl *)GpiObjHdl::m_impl)
                          ->format_to_string(m_value.format));
            return -1;
        }
    }

    if (vhpi_put_value(GpiObjHdl::get_handle<vhpiHandleT>(), &m_value,
                       map_put_value_mode(action))) {
        check_vhpi_error();
        return -1;
    }

    return 0;
}

int VhpiSignalObjHdl::set_signal_value_str(std::string &value,
                                           gpi_set_action_t action) {
    switch (m_value.format) {
        case vhpiStrVal: {
            std::vector<char> writable(value.begin(), value.end());
            writable.push_back('\0');
            strncpy(m_value.value.str, &writable[0],
                    static_cast<size_t>(m_value.numElems));
            m_value.value.str[m_value.numElems] = '\0';
            break;
        }

        default: {
            LOG_ERROR("VHPI: Unable to handle this format type: %s",
                      ((VhpiImpl *)GpiObjHdl::m_impl)
                          ->format_to_string(m_value.format));
            return -1;
        }
    }

    if (vhpi_put_value(GpiObjHdl::get_handle<vhpiHandleT>(), &m_value,
                       map_put_value_mode(action))) {
        check_vhpi_error();
        return -1;
    }

    return 0;
}

const char *VhpiSignalObjHdl::get_signal_value_binstr() {
    switch (m_value.format) {
        case vhpiRealVal:
            LOG_INFO("VHPI: get_signal_value_binstr not supported for %s",
                     ((VhpiImpl *)GpiObjHdl::m_impl)
                         ->format_to_string(m_value.format));
            return "";
        default: {
            /* Some simulators do not support BinaryValues so we fake up here
             * for them */
            int ret = vhpi_get_value(GpiObjHdl::get_handle<vhpiHandleT>(),
                                     &m_binvalue);
            if (ret) {
                check_vhpi_error();
                LOG_ERROR(
                    "VHPI: Size of m_binvalue.value.str was not large enough: "
                    "req=%d have=%d for type %s",
                    ret, m_binvalue.bufSize,
                    ((VhpiImpl *)GpiObjHdl::m_impl)
                        ->format_to_string(m_value.format));
            }

            return m_binvalue.value.str;
        }
    }
}

const char *VhpiSignalObjHdl::get_signal_value_str() {
    switch (m_value.format) {
        case vhpiStrVal: {
            int ret =
                vhpi_get_value(GpiObjHdl::get_handle<vhpiHandleT>(), &m_value);
            if (ret) {
                check_vhpi_error();
                LOG_ERROR(
                    "VHPI: Size of m_value.value.str was not large enough: "
                    "req=%d have=%d for type %s",
                    ret, m_value.bufSize,
                    ((VhpiImpl *)GpiObjHdl::m_impl)
                        ->format_to_string(m_value.format));
            }
            break;
        }
        default: {
            LOG_ERROR("VHPI: Reading strings not valid for this handle");
            return "";
        }
    }
    return m_value.value.str;
}

double VhpiSignalObjHdl::get_signal_value_real() {
    m_value.format = vhpiRealVal;
    m_value.numElems = 1;
    m_value.bufSize = sizeof(double);

    if (vhpi_get_value(GpiObjHdl::get_handle<vhpiHandleT>(), &m_value)) {
        check_vhpi_error();
        LOG_ERROR("VHPI: Failed to get value of type real");
    }
    return m_value.value.real;
}

long VhpiSignalObjHdl::get_signal_value_long() {
    vhpiValueT value;
    value.format = vhpiIntVal;
    value.numElems = 0;

    if (vhpi_get_value(GpiObjHdl::get_handle<vhpiHandleT>(), &value)) {
        check_vhpi_error();
        LOG_ERROR("VHPI: Failed to get value of type long");
    }

    return static_cast<int32_t>(value.value.intg);
}

GpiCbHdl *VhpiSignalObjHdl::value_change_cb(int edge) {
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

VhpiValueCbHdl::VhpiValueCbHdl(GpiImplInterface *impl, VhpiSignalObjHdl *sig,
                               int edge)
    : GpiCbHdl(impl), VhpiCbHdl(impl), GpiValueCbHdl(impl, sig, edge) {
    cb_data.reason = vhpiCbValueChange;
    cb_data.time = &vhpi_time;
    cb_data.obj = m_signal->get_handle<vhpiHandleT>();
}

VhpiStartupCbHdl::VhpiStartupCbHdl(GpiImplInterface *impl)
    : GpiCbHdl(impl), VhpiCbHdl(impl) {
    cb_data.reason = vhpiCbStartOfSimulation;
}

int VhpiStartupCbHdl::run_callback() {
    vhpiHandleT tool, argv_iter, argv_hdl;
    char **tool_argv = NULL;
    int tool_argc = 0;
    int i = 0;

    tool = vhpi_handle(vhpiTool, NULL);
    if (tool) {
        tool_argc = static_cast<int>(vhpi_get(vhpiArgcP, tool));
        tool_argv = new char *[tool_argc];
        assert(tool_argv);

        argv_iter = vhpi_iterator(vhpiArgvs, tool);
        if (argv_iter) {
            while ((argv_hdl = vhpi_scan(argv_iter))) {
                tool_argv[i] = const_cast<char *>(static_cast<const char *>(
                    vhpi_get_str(vhpiStrValP, argv_hdl)));
                i++;
            }
            vhpi_release_handle(argv_iter);
        }

        vhpi_release_handle(tool);
    }

    gpi_embed_init(tool_argc, tool_argv);
    delete[] tool_argv;

    return 0;
}

VhpiShutdownCbHdl::VhpiShutdownCbHdl(GpiImplInterface *impl)
    : GpiCbHdl(impl), VhpiCbHdl(impl) {
    cb_data.reason = vhpiCbEndOfSimulation;
}

int VhpiShutdownCbHdl::run_callback() {
    set_call_state(GPI_DELETE);
    gpi_embed_end();
    return 0;
}

VhpiTimedCbHdl::VhpiTimedCbHdl(GpiImplInterface *impl, uint64_t time)
    : GpiCbHdl(impl), VhpiCbHdl(impl) {
    vhpi_time.high = (uint32_t)(time >> 32);
    vhpi_time.low = (uint32_t)(time);

    cb_data.reason = vhpiCbAfterDelay;
    cb_data.time = &vhpi_time;
}

int VhpiTimedCbHdl::cleanup_callback() {
    if (m_state == GPI_FREE) return 1;

    vhpi_remove_cb(get_handle<vhpiHandleT>());

    m_obj_hdl = NULL;
    m_state = GPI_FREE;
    return 1;
}

VhpiReadwriteCbHdl::VhpiReadwriteCbHdl(GpiImplInterface *impl)
    : GpiCbHdl(impl), VhpiCbHdl(impl) {
    cb_data.reason = vhpiCbRepLastKnownDeltaCycle;
    cb_data.time = &vhpi_time;
}

VhpiReadOnlyCbHdl::VhpiReadOnlyCbHdl(GpiImplInterface *impl)
    : GpiCbHdl(impl), VhpiCbHdl(impl) {
    cb_data.reason = vhpiCbRepEndOfTimeStep;
    cb_data.time = &vhpi_time;
}

VhpiNextPhaseCbHdl::VhpiNextPhaseCbHdl(GpiImplInterface *impl)
    : GpiCbHdl(impl), VhpiCbHdl(impl) {
    cb_data.reason = vhpiCbRepNextTimeStep;
    cb_data.time = &vhpi_time;
}

decltype(VhpiIterator::iterate_over) VhpiIterator::iterate_over = [] {
    /* for reused lists */
    std::initializer_list<vhpiOneToManyT> root_options = {
        vhpiInternalRegions,
        vhpiSigDecls,
        vhpiVarDecls,
        vhpiPortDecls,
        vhpiGenericDecls,
        vhpiConstDecls,
        //    vhpiIndexedNames,
        vhpiCompInstStmts,
        vhpiBlockStmts,
    };
    std::initializer_list<vhpiOneToManyT> sig_options = {
        vhpiIndexedNames,
        vhpiSelectedNames,
    };
    std::initializer_list<vhpiOneToManyT> simplesig_options = {
        vhpiDecls,
        vhpiInternalRegions,
        vhpiSensitivitys,
        vhpiStmts,
    };
    std::initializer_list<vhpiOneToManyT> gen_options = {
        vhpiDecls,      vhpiInternalRegions, vhpiSigDecls,   vhpiVarDecls,
        vhpiConstDecls, vhpiCompInstStmts,   vhpiBlockStmts,
    };

    return decltype(VhpiIterator::iterate_over){
        {vhpiRootInstK, root_options},
        {vhpiCompInstStmtK, root_options},

        {vhpiGenericDeclK, sig_options},
        {vhpiSigDeclK, sig_options},
        {vhpiSelectedNameK, sig_options},
        {vhpiIndexedNameK, sig_options},
        {vhpiPortDeclK, sig_options},

        {vhpiCondSigAssignStmtK, simplesig_options},
        {vhpiSimpleSigAssignStmtK, simplesig_options},
        {vhpiSelectSigAssignStmtK, simplesig_options},

        {vhpiForGenerateK, gen_options},
        {vhpiIfGenerateK, gen_options},
        {vhpiBlockStmtK, gen_options},

        {vhpiConstDeclK,
         {
             vhpiAttrSpecs,
             vhpiIndexedNames,
             vhpiSelectedNames,
         }},
    };
}();

VhpiIterator::VhpiIterator(GpiImplInterface *impl, GpiObjHdl *hdl)
    : GpiIterator(impl, hdl), m_iterator(NULL), m_iter_obj(NULL) {
    vhpiHandleT iterator;
    vhpiHandleT vhpi_hdl = m_parent->get_handle<vhpiHandleT>();

    vhpiClassKindT type = (vhpiClassKindT)vhpi_get(vhpiKindP, vhpi_hdl);
    try {
        selected = &iterate_over.at(type);
    } catch (std::out_of_range const &) {
        LOG_WARN(
            "VHPI: Implementation does not know how to iterate over %s(%d)",
            vhpi_get_str(vhpiKindStrP, vhpi_hdl), type);
        selected = nullptr;
        return;
    }

    /* Find the first mapping type that yields a valid iterator */
    for (one2many = selected->begin(); one2many != selected->end();
         one2many++) {
        /* GPI_GENARRAY are pseudo-regions and all that should be searched for
         * are the sub-regions */
        if (m_parent->get_type() == GPI_GENARRAY &&
            *one2many != vhpiInternalRegions) {
            LOG_DEBUG(
                "VHPI: vhpi_iterator vhpiOneToManyT=%d skipped for "
                "GPI_GENARRAY type",
                *one2many);
            continue;
        }

        iterator = vhpi_iterator(*one2many, vhpi_hdl);

        if (iterator) break;

        LOG_DEBUG("VHPI: vhpi_iterate vhpiOneToManyT=%d returned NULL",
                  *one2many);
    }

    if (NULL == iterator) {
        LOG_DEBUG(
            "VHPI: vhpi_iterate return NULL for all relationships on %s (%d) "
            "kind:%s",
            vhpi_get_str(vhpiCaseNameP, vhpi_hdl), type,
            vhpi_get_str(vhpiKindStrP, vhpi_hdl));
        selected = NULL;
        return;
    }

    LOG_DEBUG("VHPI: Created iterator working from scope %d (%s)",
              vhpi_get(vhpiKindP, vhpi_hdl),
              vhpi_get_str(vhpiKindStrP, vhpi_hdl));

    /* On some simulators (Aldec) vhpiRootInstK is a null level of hierarchy.
     * We check that something is going to come back, if not, we try the level
     * down.
     */
    m_iter_obj = vhpi_hdl;
    m_iterator = iterator;
}

VhpiIterator::~VhpiIterator() {
    if (m_iterator) vhpi_release_handle(m_iterator);
}

#define VHPI_TYPE_MIN (1000)

GpiIterator::Status VhpiIterator::next_handle(std::string &name,
                                              GpiObjHdl **hdl, void **raw_hdl) {
    vhpiHandleT obj;
    GpiObjHdl *new_obj;

    if (!selected) return GpiIterator::END;

    gpi_objtype_t obj_type = m_parent->get_type();
    std::string parent_name = m_parent->get_name();

    /* We want the next object in the current mapping.
     * If the end of mapping is reached then we want to
     * try the next one until a new object is found.
     */
    do {
        obj = NULL;

        if (m_iterator) {
            obj = vhpi_scan(m_iterator);

            /* For GPI_GENARRAY, only allow the generate statements through that
             * match the name of the generate block.
             */
            if (obj != NULL && obj_type == GPI_GENARRAY) {
                if (vhpi_get(vhpiKindP, obj) == vhpiForGenerateK) {
                    std::string rgn_name = vhpi_get_str(vhpiCaseNameP, obj);
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

            if (obj != NULL &&
                (vhpiProcessStmtK == vhpi_get(vhpiKindP, obj) ||
                 vhpiCondSigAssignStmtK == vhpi_get(vhpiKindP, obj) ||
                 vhpiSimpleSigAssignStmtK == vhpi_get(vhpiKindP, obj) ||
                 vhpiSelectSigAssignStmtK == vhpi_get(vhpiKindP, obj))) {
                LOG_DEBUG("VHPI: Skipping %s (%s)",
                          vhpi_get_str(vhpiFullNameP, obj),
                          vhpi_get_str(vhpiKindStrP, obj));
                obj = NULL;
                continue;
            }

            if (obj != NULL) {
                LOG_DEBUG("VHPI: Found an item %s",
                          vhpi_get_str(vhpiFullNameP, obj));
                break;
            } else {
                LOG_DEBUG("VHPI: vhpi_scan on vhpiOneToManyT=%d returned NULL",
                          *one2many);
            }

            LOG_DEBUG("VHPI: End of vhpiOneToManyT=%d iteration", *one2many);
            m_iterator = NULL;
        } else {
            LOG_DEBUG("VHPI: No valid vhpiOneToManyT=%d iterator", *one2many);
        }

        if (++one2many >= selected->end()) {
            obj = NULL;
            break;
        }

        /* GPI_GENARRAY are pseudo-regions and all that should be searched for
         * are the sub-regions */
        if (obj_type == GPI_GENARRAY && *one2many != vhpiInternalRegions) {
            LOG_DEBUG(
                "VHPI: vhpi_iterator vhpiOneToManyT=%d skipped for "
                "GPI_GENARRAY type",
                *one2many);
            continue;
        }

        m_iterator = vhpi_iterator(*one2many, m_iter_obj);

    } while (!obj);

    if (NULL == obj) {
        LOG_DEBUG("VHPI: No more children, all relationships have been tested");
        return GpiIterator::END;
    }

    const char *c_name = vhpi_get_str(vhpiCaseNameP, obj);
    if (!c_name) {
        vhpiIntT type = vhpi_get(vhpiKindP, obj);

        if (type < VHPI_TYPE_MIN) {
            *raw_hdl = (void *)obj;
            return GpiIterator::NOT_NATIVE_NO_NAME;
        }

        LOG_DEBUG(
            "VHPI: Unable to get the name for this object of type " PRIu32,
            type);

        return GpiIterator::NATIVE_NO_NAME;
    }

    /*
     * If the parent is not a generate loop, then watch for generate handles and
     * create the pseudo-region.
     *
     * NOTE: Taking advantage of the "caching" to only create one pseudo-region
     * object. Otherwise a list would be required and checked while iterating
     */
    if (*one2many == vhpiInternalRegions && obj_type != GPI_GENARRAY &&
        vhpi_get(vhpiKindP, obj) == vhpiForGenerateK) {
        std::string idx_str = c_name;
        std::size_t found = idx_str.rfind(GEN_IDX_SEP_LHS);

        if (found != std::string::npos && found != 0) {
            name = idx_str.substr(0, found);
            obj = m_parent->get_handle<vhpiHandleT>();
        } else {
            LOG_WARN("VHPI: Unhandled Generate Loop Format - %s", name.c_str());
            name = c_name;
        }
    } else {
        name = c_name;
    }

    LOG_DEBUG("VHPI: vhpi_scan found %s (%d) kind:%s name:%s", name.c_str(),
              vhpi_get(vhpiKindP, obj), vhpi_get_str(vhpiKindStrP, obj),
              vhpi_get_str(vhpiCaseNameP, obj));

    /* We try and create a handle internally, if this is not possible we
       return and GPI will try other implementations with the name
       */
    std::string fq_name = m_parent->get_fullname();
    if (fq_name == ":") {
        fq_name += name;
    } else if (obj_type == GPI_GENARRAY) {
        std::size_t found = name.rfind(GEN_IDX_SEP_LHS);

        if (found != std::string::npos) {
            fq_name += name.substr(found);
        } else {
            LOG_WARN("VHPI: Unhandled Sub-Element Format - %s", name.c_str());
            fq_name += "." + name;
        }
    } else if (obj_type == GPI_STRUCTURE) {
        std::size_t found = name.rfind(".");

        if (found != std::string::npos) {
            fq_name += name.substr(found);
            name = name.substr(found + 1);
        } else {
            LOG_WARN("VHPI: Unhandled Sub-Element Format - %s", name.c_str());
            fq_name += "." + name;
        }
    } else {
        fq_name += "." + name;
    }
    VhpiImpl *vhpi_impl = reinterpret_cast<VhpiImpl *>(m_impl);
    new_obj = vhpi_impl->create_gpi_obj_from_handle(obj, name, fq_name);
    if (new_obj) {
        *hdl = new_obj;
        return GpiIterator::NATIVE;
    } else
        return GpiIterator::NOT_NATIVE;
}
