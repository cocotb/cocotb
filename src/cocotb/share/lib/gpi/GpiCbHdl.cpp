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

void GpiEdgeCbScheduler::init(GpiEdgeCbHdl *cbh) {
    cbh->it = tracker[cbh->edge - 1].cbm.end();
}

int GpiEdgeCbScheduler::arm(GpiEdgeCbHdl *cbh) {
    EdgeCbMap &cbmap = tracker[cbh->edge - 1].cbm;
    if (cbh->it != cbmap.end()) {
        cbmap.erase(cbh->it);
    }
    cbh->it = cbmap.emplace(tracker[cbh->edge - 1].ctr + cbh->count + 1, cbh);
    total_cb_count++;
    if (total_cb_count == 1) {
        if (track_edges() != 0) {
            cleanup(cbh);
            return -1;
        }
    }

    return 0;
}

void GpiEdgeCbScheduler::cleanup(GpiEdgeCbHdl *cbh) {
    EdgeCbMap &cbmap = tracker[cbh->edge - 1].cbm;
    if (cbh->it != cbmap.end()) {
        cbmap.erase(cbh->it);
        cbh->it = cbmap.end();
        --total_cb_count;
    }
}

bool GpiEdgeCbScheduler::process_edge(bool rising, bool falling) {
    if (rising) {
        tracker[0].on_edge();
    }
    if (falling) {
        tracker[1].on_edge();
    }
    tracker[2].on_edge();

    return (total_cb_count != 0);
}

GpiEdgeCbScheduler::EdgeCbTracker::~EdgeCbTracker() {
    if (!cbm.empty()) {
        LOG_WARN("EdgeCbTracker not empty on destruction")
        for (std::pair<const uint64_t, GpiEdgeCbHdl *> &kv : cbm) {
            kv.second->scheduler = nullptr;
        }
    }
}

void GpiEdgeCbScheduler::EdgeCbTracker::on_edge() {
    if (cbm.empty()) {
        return;
    }

    EdgeCbMap::iterator it = cbm.lower_bound(ctr);

    while (it != cbm.end()) {
        if (it->first != ctr) break;
        GpiEdgeCbHdl *cb = it->second;
        // increment iterator here: deleting/cleaning up cb will remove from
        // map and decrease counter.
        ++it;
        cb->run_callback();
        delete cb;
    }

    ctr++;
}

GpiEdgeCbHdl::GpiEdgeCbHdl(GpiEdgeCbScheduler *_scheduler,
                           GpiImplInterface *impl, int _edge, uint64_t _count)
    : GpiCbHdl(impl),
      GpiCommonCbHdl(impl),
      edge(_edge),
      count(_count),
      scheduler(_scheduler) {
    scheduler->init(this);
}

GpiEdgeCbHdl::~GpiEdgeCbHdl() {
    if (scheduler) {
        scheduler->cleanup(this);
    }
}

int GpiEdgeCbHdl::arm_callback() {
    if (scheduler) {
        return scheduler->arm(this);
    } else {
        return -1;
    }
}

int GpiEdgeCbHdl::cleanup_callback() {
    if (scheduler) {
        scheduler->cleanup(this);
    }
    return 1;
}
