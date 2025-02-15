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

#include "VpiImpl.h"
#include "gpi_logging.h"

#ifndef VPI_NO_QUEUE_SETIMMEDIATE_CALLBACKS
#include <algorithm>
#include <deque>

static std::deque<GpiCbHdl *> cb_queue;
#endif

static int32_t handle_vpi_callback_(GpiCbHdl *cb_hdl) {
    gpi_to_user();

    // LCOV_EXCL_START
    if (!cb_hdl) {
        LOG_CRITICAL("VPI: Callback data corrupted: ABORTING");
        gpi_embed_end();
        return -1;
    }
    // LCOV_EXCL_STOP

    cb_hdl->run();

    gpi_to_simulator();
    return 0;
}

// Main re-entry point for callbacks from simulator
int32_t handle_vpi_callback(p_cb_data cb_data) {
#ifdef VPI_NO_QUEUE_SETIMMEDIATE_CALLBACKS
    VpiCbHdl *cb_hdl = (VpiCbHdl *)cb_data->user_data;
    return handle_vpi_callback_(cb_hdl);
#else
    // must push things into a queue because Icaurus (gh-4067), Xcelium
    // (gh-4013), and Questa (gh-4105) react to value changes on signals that
    // are set with vpiNoDelay immediately, and not after the current callback
    // has ended, causing re-entrancy.
    static bool reacting = false;
    VpiCbHdl *cb_hdl = (VpiCbHdl *)cb_data->user_data;
    if (reacting) {
        cb_queue.push_back(cb_hdl);
        return 0;
    }
    reacting = true;
    int32_t ret = handle_vpi_callback_(cb_hdl);
    while (!cb_queue.empty()) {
        handle_vpi_callback_(cb_queue.front());
        cb_queue.pop_front();
    }
    reacting = false;
    return ret;
#endif
}

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

int VpiCbHdl::arm() {
    vpiHandle new_hdl = vpi_register_cb(&cb_data);

    if (!new_hdl) {
        LOG_ERROR(
            "VPI: Unable to register a callback handle for VPI type %s(%d)",
            m_impl->reason_to_string(cb_data.reason), cb_data.reason);
        check_vpi_error();
        return -1;
    }

    m_obj_hdl = new_hdl;

    return 0;
}

int VpiCbHdl::remove() {
#ifndef VPI_NO_QUEUE_SETIMMEDIATE_CALLBACKS
    // check if it's already fired and is in callback queue
    auto it = std::find(cb_queue.begin(), cb_queue.end(), this);
    if (it != cb_queue.end()) {
        cb_queue.erase(it);
        // In Verilator some callbacks are recurring, so we *should* try to
        // remove by falling through to the code below. Other sims don't like
        // removing callbacks that have already fired.
#ifndef VERILATOR
        // It's already fired, we shouldn't try to vpi_remove_cb() it now.
        delete this;
        return 0;
#endif
    }
#endif

    auto err = vpi_remove_cb(get_handle<vpiHandle>());
    // LCOV_EXCL_START
    if (!err) {
        LOG_WARN("VPI: Unable to remove callback");
        check_vpi_error();
        // put it in a removed state so if it fires we can squash it
        m_removed = true;
    }
    // LCOV_EXCL_STOP
    else {
        delete this;
    }
    return 0;
}

int VpiCbHdl::run() {
    // LCOV_EXCL_START
    if (!m_removed) {
        // Only call up if not removed.
        m_cb_func(m_cb_data);
    }
    // LCOV_EXCL_STOP

// Verilator seems to think some callbacks are recurring that Icarus and other
// sims do not. So we remove all callbacks here after firing because Verilator
// doesn't seem to mind (other sims do).
#ifdef VERILATOR
    // Remove recurring callback once fired
    auto err = vpi_remove_cb(get_handle<vpiHandle>());
    // LCOV_EXCL_START
    if (!err) {
        LOG_WARN("VPI: Unable to remove callback");
        check_vpi_error();
        // put it in a removed state so if it fires we can squash it
        m_removed = true;
    }
    // LCOV_EXCL_STOP
    else {
        delete this;
    }
#endif

    return 0;
}

VpiValueCbHdl::VpiValueCbHdl(GpiImplInterface *impl, VpiSignalObjHdl *signal,
                             gpi_edge edge)
    : VpiCbHdl(impl), m_signal(signal), m_edge(edge) {
    vpi_time.type = vpiSuppressTime;
    m_vpi_value.format = vpiIntVal;

    cb_data.reason = cbValueChange;
    cb_data.time = &vpi_time;
    cb_data.value = &m_vpi_value;
    cb_data.obj = m_signal->get_handle<vpiHandle>();
}

int VpiValueCbHdl::run() {
    // LCOV_EXCL_START
    if (m_removed) {
        // Only call up if not removed.
        return 0;
    }
    // LCOV_EXCL_STOP

    bool pass = false;
    switch (m_edge) {
        case GPI_RISING: {
            pass = !strcmp(m_signal->get_signal_value_binstr(), "1");
            break;
        }
        case GPI_FALLING: {
            pass = !strcmp(m_signal->get_signal_value_binstr(), "0");
            break;
        }
        case GPI_VALUE_CHANGE: {
            pass = true;
            break;
        }
    }

    if (pass) {
        m_cb_func(m_cb_data);

        // Remove recurring callback once fired.
        auto err = vpi_remove_cb(get_handle<vpiHandle>());
        // LCOV_EXCL_START
        if (!err) {
            LOG_WARN("VPI: Unable to remove callback");
            check_vpi_error();
            // If we fail to remove the callback, put it in a removed state so
            // if it fires we can squash it.
            m_removed = true;
        }
        // LCOV_EXCL_STOP
        else {
            delete this;
        }
    }  // else Don't remove and let it fire again.

    return 0;
}

VpiStartupCbHdl::VpiStartupCbHdl(GpiImplInterface *impl) : VpiCbHdl(impl) {
#ifndef IUS
    cb_data.reason = cbStartOfSimulation;
#else
    vpi_time.high = (uint32_t)(0);
    vpi_time.low = (uint32_t)(0);
    vpi_time.type = vpiSimTime;
    cb_data.reason = cbAfterDelay;
#endif
}

VpiShutdownCbHdl::VpiShutdownCbHdl(GpiImplInterface *impl) : VpiCbHdl(impl) {
    cb_data.reason = cbEndOfSimulation;
}

VpiTimedCbHdl::VpiTimedCbHdl(GpiImplInterface *impl, uint64_t time)
    : VpiCbHdl(impl) {
    vpi_time.high = (uint32_t)(time >> 32);
    vpi_time.low = (uint32_t)(time);
    vpi_time.type = vpiSimTime;

    cb_data.reason = cbAfterDelay;
}

VpiReadWriteCbHdl::VpiReadWriteCbHdl(GpiImplInterface *impl) : VpiCbHdl(impl) {
    cb_data.reason = cbReadWriteSynch;
}

VpiReadOnlyCbHdl::VpiReadOnlyCbHdl(GpiImplInterface *impl) : VpiCbHdl(impl) {
    cb_data.reason = cbReadOnlySynch;
}

VpiNextPhaseCbHdl::VpiNextPhaseCbHdl(GpiImplInterface *impl) : VpiCbHdl(impl) {
    cb_data.reason = cbNextSimTime;
}
