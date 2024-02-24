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
