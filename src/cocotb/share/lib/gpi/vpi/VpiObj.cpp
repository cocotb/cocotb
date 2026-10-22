// Copyright cocotb contributors
// Copyright (c) 2013, 2018 Potential Ventures Ltd
// Copyright (c) 2013 SolarFlare Communications Inc
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include <algorithm>

#include "../logging.hpp"
#include "./VpiImpl.hpp"
#include "_vendor/vpi/sv_vpi_user.h"

VpiArrayObjHdl::~VpiArrayObjHdl() {
    if (m_owns_handle) vpi_free_object(get_handle<vpiHandle>());
}

VpiObjHdl::~VpiObjHdl() {
    // Generate pseudo-regions borrow their containing region's handle.
    if (m_type != GPI_GENARRAY) vpi_free_object(get_handle<vpiHandle>());
}

int get_range_bounds(vpiHandle obj, int &left, int &right) {
    s_vpi_value val;
    val.format = vpiIntVal;

    vpiHandle leftRange = vpi_handle(vpiLeftRange, obj);
    // LCOV_EXCL_START
    if (leftRange == NULL) {
        return -1;
    }
    // LCOV_EXCL_STOP
    vpi_get_value(leftRange, &val);
    left = val.value.integer;
    vpi_free_object(leftRange);

    vpiHandle rightRange = vpi_handle(vpiRightRange, obj);
    // LCOV_EXCL_START
    if (rightRange == NULL) {
        return -1;
    }
    // LCOV_EXCL_STOP
    vpi_get_value(rightRange, &val);
    right = val.value.integer;
    vpi_free_object(rightRange);

    return 0;
}

int VpiArrayObjHdl::initialise(const std::string &name,
                               const std::string &fq_name) {
    vpiHandle hdl = GpiObjHdl::get_handle<vpiHandle>();

    m_indexable = true;

    int range_idx = 0;

    /* Need to determine if this is a pseudo-handle to be able to select the
     * correct range */
    std::string hdl_name = vpi_get_str(vpiName, hdl);

    /* Removing the hdl_name from the name will leave the pseudo-indices */
    if (hdl_name.length() < name.length()) {
        // get the last index of hdl_name in name
        std::size_t idx_str = name.rfind(hdl_name);
        if (idx_str == std::string::npos) {
            LOG_ERROR("Unable to find name %s in %s", hdl_name.c_str(),
                      name.c_str());
            return -1;
        }
        // count occurrences of [
        auto start =
            name.begin() + static_cast<std::string::difference_type>(idx_str);
        range_idx = static_cast<int>(std::count(start, name.end(), '['));
    }

    /* After determining the range_idx, get the range and set the limits */
    vpiHandle iter = vpi_iterate(vpiRange, hdl);

    if (iter != NULL) {
        vpiHandle rangeHdl = vpi_scan(iter);

// Questa and VCS vpiRange iter always starts from the first index of the array.
#if defined(MODELSIM) || defined(VCS)
        for (int i = 0; rangeHdl != NULL && i < range_idx; ++i) {
            vpi_free_object(rangeHdl);
            rangeHdl = vpi_scan(iter);
        }
#endif
        if (rangeHdl == NULL) {
            // vpi_scan has already freed the exhausted iterator.
            LOG_ERROR("Unable to get range for indexable array");
            return -1;
        }
        DEFER(vpi_free_object(iter));
        DEFER(vpi_free_object(rangeHdl));

        int res = get_range_bounds(rangeHdl, m_range_left, m_range_right);
        // LCOV_EXCL_START
        if (res) {
            LOG_ERROR("Unable to get range bounds for indexable array: %s",
                      name.c_str());
            return -1;
        }
        // LCOV_EXCL_STOP
    } else if (range_idx == 0) {
        // iter == NULL, so no looking through multiple dimensions is possible,
        // but perhaps we can get the first dimension.
        int res = get_range_bounds(hdl, m_range_left, m_range_right);
        // LCOV_EXCL_START
        if (res) {
            LOG_ERROR("Unable to get range bounds for indexable array: %s",
                      name.c_str());
            return -1;
        }
        // LCOV_EXCL_STOP
    }
    // LCOV_EXCL_START
    else {
        LOG_ERROR("Unable to get range for indexable array or memory");
        return -1;
    }
    // LCOV_EXCL_STOP

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
        m_range_dir = GPI_RANGE_DOWN;
    } else {
        m_num_elems = m_range_right - m_range_left + 1;
        m_range_dir = GPI_RANGE_UP;
    }

    return GpiObjHdl::initialise(name, fq_name);
}

const char *VpiObjHdl::get_definition_name() {
    if (m_definition_name.empty()) {
        auto hdl = get_handle<vpiHandle>();
        auto *str = vpi_get_str(vpiDefName, hdl);
        if (str != NULL) {
            m_definition_name = str;
        }
    }
    return m_definition_name.c_str();
}

const char *VpiObjHdl::get_definition_file() {
    if (m_definition_file.empty()) {
        auto hdl = GpiObjHdl::get_handle<vpiHandle>();
        auto *str = vpi_get_str(vpiDefFile, hdl);
        if (str != NULL) {
            m_definition_file = str;
        }
    }
    return m_definition_file.c_str();
}

int VpiSignalObjHdl::get_signed() {
    return vpi_get(vpiSigned, get_handle<vpiHandle>());
}
