// Copyright cocotb contributors
// Copyright (c) 2013 Potential Ventures Ltd
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include <cassert>
#include <cinttypes>  // fixed-size int types and format strings
#include <cstring>
#include <limits>  // numeric_limits

#include "./VhpiImpl.hpp"
#include "_vendor/vhpi/vhpi_user.h"

namespace {
using bufSize_type = decltype(vhpiValueT::bufSize);
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

    LOG_DEBUG("VHPI: Releasing VhpiSignalObjHdl handle for %s at %p",
              get_fullname_str(), (void *)get_handle<vhpiHandleT>());
    if (vhpi_release_handle(get_handle<vhpiHandleT>())) check_vhpi_error();
}

vhpiPutValueModeT map_put_value_mode(gpi_set_action action) {
    vhpiPutValueModeT put_value_mode = vhpiDeposit;
    switch (action) {
        case GPI_DEPOSIT:
        case GPI_NO_DELAY:
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

int VhpiSignalObjHdl::initialise(const std::string &name,
                                 const std::string &fq_name) {
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
        name.c_str(), VhpiImpl::format_to_string(m_value.format),
        m_value.format, m_value.numElems, m_value.bufSize,
        vhpi_get(vhpiSizeP, handle));

    // Default - overridden below in certain special cases
    m_num_elems = m_value.numElems;

    switch (m_value.format) {
        case vhpiIntVal:
        case vhpiEnumVal:
        case vhpiSmallEnumVal:
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
                VhpiImpl::format_to_string(m_value.format), m_value.format);
            return -1;
        }
    }

    if (m_indexable &&
        get_range(handle, 0, &m_range_left, &m_range_right, &m_range_dir)) {
        m_indexable = false;
    }

    if (m_num_elems) {
        int bufSize = m_num_elems * static_cast<int>(sizeof(vhpiCharT)) + 1;
        m_binvalue.bufSize = static_cast<bufSize_type>(bufSize);
        m_binvalue.value.str = new vhpiCharT[bufSize];
    }

    return GpiObjHdl::initialise(name, fq_name);
}

int VhpiLogicSignalObjHdl::initialise(const std::string &name,
                                      const std::string &fq_name) {
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
        LOG_DEBUG("VHPI: Null vector... Delete object");
        return -1;
    }

    if (vhpi_get(vhpiKindP, query_hdl) == vhpiArrayTypeDeclK) {
        m_indexable = true;
        m_value.format = vhpiLogicVecVal;
        int bufSize = m_num_elems * static_cast<int>(sizeof(vhpiEnumT));
        m_value.bufSize = static_cast<bufSize_type>(bufSize);
        m_value.value.enumvs = new vhpiEnumT[bufSize];
    }

    if (m_indexable &&
        get_range(handle, 0, &m_range_left, &m_range_right, &m_range_dir)) {
        m_indexable = false;
    }

    if (m_num_elems) {
        int bufSize = m_num_elems * static_cast<int>(sizeof(vhpiCharT)) + 1;
        m_binvalue.bufSize = static_cast<bufSize_type>(bufSize);
        m_binvalue.value.str = new vhpiCharT[bufSize];
    }

    return GpiObjHdl::initialise(name, fq_name);
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
        case 'W':
        case 'w':
            return vhpiW;
        case 'L':
        case 'l':
            return vhpiL;
        case 'H':
        case 'h':
            return vhpiH;
        case '-':
            return vhpiDontCare;
        default:
            LOG_ERROR("VHPI: Character '%c' is not a valid vhpiEnumT", value);
            return vhpiDontCare;
    }
}

// Value related functions
int VhpiLogicSignalObjHdl::set_signal_value(int32_t value,
                                            gpi_set_action action) {
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
                                                   gpi_set_action action) {
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
int VhpiSignalObjHdl::set_signal_value(int32_t value, gpi_set_action action) {
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

        case vhpiSmallEnumVal: {
            m_value.value.smallenumv = static_cast<vhpiSmallEnumT>(value);
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
                      VhpiImpl::format_to_string(m_value.format));
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

int VhpiSignalObjHdl::set_signal_value(double value, gpi_set_action action) {
    switch (m_value.format) {
        case vhpiRealVal:
            m_value.numElems = 1;
            m_value.bufSize = sizeof(value);
            m_value.value.real = value;
            break;

        default: {
            LOG_ERROR("VHPI: Unable to set a Real handle with format type %s",
                      VhpiImpl::format_to_string(m_value.format));
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
                                              gpi_set_action action) {
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
                      VhpiImpl::format_to_string(m_value.format));
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
                                           gpi_set_action action) {
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
                      VhpiImpl::format_to_string(m_value.format));
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
                     VhpiImpl::format_to_string(m_value.format));
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
                    VhpiImpl::format_to_string(m_value.format));
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
                    VhpiImpl::format_to_string(m_value.format));
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

GpiCbHdl *VhpiSignalObjHdl::register_value_change_callback(
    gpi_edge edge, int (*cb_func)(void *), void *cb_data) {
    auto cb_hdl = new VhpiValueCbHdl(m_impl, this, edge);
    auto err = cb_hdl->arm();
    // LCOV_EXCL_START
    if (err) {
        delete cb_hdl;
        return NULL;
    }
    // LCOV_EXCL_STOP
    cb_hdl->set_cb_info(cb_func, cb_data);
    return cb_hdl;
}
