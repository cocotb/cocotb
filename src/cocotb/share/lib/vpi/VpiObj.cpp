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

#include <algorithm>
#include <stdexcept>

#include "VpiImpl.h"

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
        // count occurences of [
        auto start =
            name.begin() + static_cast<std::string::difference_type>(idx_str);
        range_idx = static_cast<int>(std::count(start, name.end(), '['));
    }

    /* After determining the range_idx, get the range and set the limits */
    vpiHandle iter = vpi_iterate(vpiRange, hdl);
    vpiHandle rangeHdl;

    if (iter != NULL) {
        rangeHdl = vpi_scan(iter);

        for (int i = 0; i < range_idx; ++i) {
            rangeHdl = vpi_scan(iter);
            if (rangeHdl == NULL) {
                break;
            }
        }
        if (rangeHdl == NULL) {
            LOG_ERROR("Unable to get range for indexable array");
            return -1;
        }
        vpi_free_object(iter);  // Need to free iterator since exited early
    } else if (range_idx == 0) {
        rangeHdl = hdl;
    } else {
        LOG_ERROR("Unable to get range for indexable array or memory");
        return -1;
    }

    s_vpi_value val;
    val.format = vpiIntVal;
    vpi_get_value(vpi_handle(vpiLeftRange, rangeHdl), &val);
    check_vpi_error();
    m_range_left = val.value.integer;

    vpi_get_value(vpi_handle(vpiRightRange, rangeHdl), &val);
    check_vpi_error();
    m_range_right = val.value.integer;

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
