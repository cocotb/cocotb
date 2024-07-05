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

#include <climits>

#include "gpi_priv.h"

const char *GpiObjHdl::get_name_str() { return m_name.c_str(); }

const char *GpiObjHdl::get_fullname_str() { return m_fullname.c_str(); }

const std::string &GpiObjHdl::get_fullname() { return m_fullname; }

const char *GpiObjHdl::get_type_str() {
#define CASE_OPTION(_X) \
    case _X:            \
        ret = #_X;      \
        break

    const char *ret;

    switch (m_type) {
        CASE_OPTION(GPI_UNKNOWN);
        CASE_OPTION(GPI_MEMORY);
        CASE_OPTION(GPI_MODULE);
        CASE_OPTION(GPI_NET);
        // CASE_OPTION(GPI_PARAMETER);  // Deprecated
        CASE_OPTION(GPI_REGISTER);
        CASE_OPTION(GPI_ARRAY);
        CASE_OPTION(GPI_ENUM);
        CASE_OPTION(GPI_STRUCTURE);
        CASE_OPTION(GPI_REAL);
        CASE_OPTION(GPI_INTEGER);
        CASE_OPTION(GPI_STRING);
        CASE_OPTION(GPI_GENARRAY);
        CASE_OPTION(GPI_PACKAGE);
        default:
            ret = "unknown";
    }

    return ret;
}

const std::string &GpiObjHdl::get_name() { return m_name; }

/* Genertic base clss implementations */
bool GpiHdl::is_this_impl(GpiImplInterface *impl) {
    return impl == this->m_impl;
}

int GpiObjHdl::initialise(const std::string &name, const std::string &fq_name) {
    m_name = name;
    m_fullname = fq_name;
    return 0;
}

void GpiCbHdl::set_call_state(gpi_cb_state_e new_state) { m_state = new_state; }

gpi_cb_state_e GpiCbHdl::get_call_state() { return m_state; }

GpiCbHdl::~GpiCbHdl() {}

int GpiCommonCbHdl::run_callback() {
    this->gpi_function(m_cb_data);
    return 0;
}

int GpiCommonCbHdl::set_user_data(int (*gpi_function)(void *), void *data) {
    if (!gpi_function) {
        LOG_ERROR("gpi_function to set_user_data is NULL");
    }
    this->gpi_function = gpi_function;
    this->m_cb_data = data;
    return 0;
}

GpiValueCbHdl::GpiValueCbHdl(GpiImplInterface *impl, GpiSignalObjHdl *signal,
                             int edge)
    : GpiCbHdl(impl), GpiCommonCbHdl(impl), m_signal(signal) {
    if (edge == (GPI_RISING | GPI_FALLING))
        required_value = "X";
    else if (edge & GPI_RISING)
        required_value = "1";
    else if (edge & GPI_FALLING)
        required_value = "0";
}

int GpiValueCbHdl::run_callback() {
    std::string current_value;
    bool pass = false;

    if (required_value == "X")
        pass = true;
    else {
        current_value = m_signal->get_signal_value_binstr();
        if (current_value == required_value) pass = true;
    }

    if (pass) {
        this->gpi_function(m_cb_data);
    } else {
        cleanup_callback();
        arm_callback();
    }

    return 0;
}

// TODO -- VHPI specialization possibly using vhpiInVecVal or vhpiPtrVal
int GpiSignalObjHdl::get_signal_value_bytes(char *buffer, size_t size,
                                            gpi_resolve_x_t resolve_x) {
    const char *binstr = get_signal_value_binstr();
    size_t binstr_len = strlen(binstr);
    size_t len = std::min(binstr_len, size * 8);

    unsigned char curr = 0x0;
    for (unsigned int bit = 0; bit < len; bit++) {
        int offset = bit % 8;
        unsigned char bit_val;
        char bit_char = binstr[binstr_len - 1 - bit];
        if (bit_char == '0') {
            bit_val = 0;
        } else if (bit_char == '1') {
            bit_val = 1;
        } else if (resolve_x == GPI_X_ONES) {
            bit_val = 1;
        } else if (resolve_x == GPI_X_ZEROS) {
            bit_val = 0;
        } else if (resolve_x == GPI_X_RANDOM) {
            bit_val = gpi_rand() & 0x1;
        } else {  // GPI_X_ERROR
            return -1;
        }
        curr |= static_cast<unsigned char>(bit_val << offset);
        if (bit % 8 == 7 || bit + 1 == len) {
            int byte = bit / 8;
            buffer[byte] = static_cast<char>(curr);
            curr = 0x0;
        }
    }

    return 0;
}

int GpiSignalObjHdl::set_signal_value_bytes(const char *buffer, size_t,
                                            gpi_set_action_t action) {
    std::string str;
    size_t chars = static_cast<size_t>(m_num_elems);
    str.resize(chars);

    for (unsigned int bit = 0; bit < chars; bit++) {
        int byte = bit / 8;
        int offset = bit % 8;
        str[chars - 1 - bit] = (buffer[byte] >> offset) & 0x1 ? '1' : '0';
    }

    return set_signal_value_binstr(str, action);
}
