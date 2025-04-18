// Copyright cocotb contributors
// Copyright (c) 2013, 2018 Potential Ventures Ltd
// Copyright (c) 2013 SolarFlare Communications Inc
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include "VpiImpl.h"
#include "gpi_logging.h"
#include "share/lib/gpi/gpi_priv.h"

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

    if (cb_hdl->run()) {
        // sim failed, so call shutdown
        gpi_embed_end();
        return 0;
    }

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
        LOG_DEBUG("VPI: Unable to remove callback");
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
    int res = 0;

    // LCOV_EXCL_START
    if (!m_removed) {
        // Only call up if not removed.
        res = m_cb_func(m_cb_data);
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
        LOG_DEBUG("VPI: Unable to remove callback");
        check_vpi_error();
        // put it in a removed state so if it fires we can squash it
        m_removed = true;
    }
    // LCOV_EXCL_STOP
    else {
        delete this;
    }
#endif

    return res;
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

    int res = 0;
    if (pass) {
        res = m_cb_func(m_cb_data);

        // Remove recurring callback once fired.
        auto err = vpi_remove_cb(get_handle<vpiHandle>());
        // LCOV_EXCL_START
        if (!err) {
            LOG_DEBUG("VPI: Unable to remove callback");
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

    return res;
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
