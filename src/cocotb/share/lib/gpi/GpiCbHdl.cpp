// Copyright cocotb contributors
// Copyright (c) 2013 Potential Ventures Ltd
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include "gpi.h"
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
        CASE_OPTION(GPI_ARRAY);
        CASE_OPTION(GPI_ENUM);
        CASE_OPTION(GPI_STRUCTURE);
        CASE_OPTION(GPI_REAL);
        CASE_OPTION(GPI_INTEGER);
        CASE_OPTION(GPI_STRING);
        CASE_OPTION(GPI_GENARRAY);
        CASE_OPTION(GPI_PACKAGE);
        CASE_OPTION(GPI_LOGIC);
        CASE_OPTION(GPI_LOGIC_ARRAY);
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
