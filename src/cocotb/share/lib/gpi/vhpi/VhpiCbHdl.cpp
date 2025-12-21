// Copyright cocotb contributors
// Copyright (c) 2013 Potential Ventures Ltd
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include <cinttypes>  // fixed-size int types and format strings
#include <cstring>

#include "./VhpiImpl.hpp"
#include "_vendor/vhpi/vhpi_user.h"

// Main entry point for callbacks from simulator
void handle_vhpi_callback(const vhpiCbDataT *cb_data) {
    SIM_TO_GPI(VHPI, VhpiImpl::reason_to_string(cb_data->reason));

    VhpiCbHdl *cb_hdl = (VhpiCbHdl *)cb_data->user_data;

    int error = (!cb_hdl);
    // LCOV_EXCL_START
    if (error) {
        LOG_CRITICAL("VHPI: Callback data corrupted: ABORTING");
    }
    // LCOV_EXCL_STOP

    if (!error) {
        GPI_TO_USER_CB(VHPI);
        error = cb_hdl->run();
        USER_CB_TO_GPI(VHPI);
    }

    if (error) {
        gpi_end_of_sim_time();
    }

    GPI_TO_SIM(VHPI);
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

int VhpiCbHdl::remove() {
    auto err = vhpi_remove_cb(get_handle<vhpiHandleT>());
    // LCOV_EXCL_START
    if (err) {
        LOG_DEBUG("VHPI: Unable to remove callback!");
        check_vhpi_error();
        // If we fail to remove the callback, mark it as removed so once it
        // fires we can squash it then remove the callback cleanly.
        m_removed = true;
    }
    // LCOV_EXCL_STOP
    else {
        delete this;
    }
    return 0;
}

int VhpiCbHdl::arm() {
    vhpiHandleT new_hdl = vhpi_register_cb(&cb_data, vhpiReturnCb);

    // LCOV_EXCL_START
    if (!new_hdl) {
        check_vhpi_error();
        LOG_ERROR(
            "VHPI: Unable to register a callback handle for VHPI type "
            "%s(%d)",
            VhpiImpl::reason_to_string(cb_data.reason), cb_data.reason);
        check_vhpi_error();
        return -1;
    }
    // LCOV_EXCL_STOP

    m_obj_hdl = new_hdl;
    return 0;
}

int VhpiCbHdl::run() {
    int res = 0;

    // LCOV_EXCL_START
    if (!m_removed) {
        // Only call up if not removed.
        res = m_cb_func(m_cb_data);
    }
    // LCOV_EXCL_STOP

    // Many callbacks in VHPI are recurring, so we try to remove them after they
    // fire. For the callbacks that aren't recurring, this doesn't seem to make
    // the simulator unhappy, so whatever.
    auto err = vhpi_remove_cb(get_handle<vhpiHandleT>());
    // LCOV_EXCL_START
    if (err) {
        LOG_DEBUG("VHPI: Unable to remove callback!");
        check_vhpi_error();
        // If we fail to remove the callback, mark it as removed so if it fires
        // we can squash it.
        m_removed = true;
    }
    // LCOV_EXCL_STOP
    else {
        delete this;
    }
    return res;
}

VhpiValueCbHdl::VhpiValueCbHdl(GpiImplInterface *impl, VhpiSignalObjHdl *sig,
                               gpi_edge edge)
    : VhpiCbHdl(impl), m_signal(sig), m_edge(edge) {
    cb_data.reason = vhpiCbValueChange;
    cb_data.time = &vhpi_time;
    cb_data.obj = m_signal->get_handle<vhpiHandleT>();
}

int VhpiValueCbHdl::run() {
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

        // Remove recurring callback once fired
        auto err = vhpi_remove_cb(get_handle<vhpiHandleT>());
        // LCOV_EXCL_START
        if (err) {
            LOG_DEBUG("VHPI: Unable to remove callback!");
            check_vhpi_error();
            // If we fail to remove the callback, mark it as removed so if it
            // fires we can squash it.
            m_removed = true;
        }
        // LCOV_EXCL_STOP
        else {
            delete this;
        }

    }  // else Don't remove and let it fire again.

    return res;
}

VhpiStartupCbHdl::VhpiStartupCbHdl(GpiImplInterface *impl) : VhpiCbHdl(impl) {
    cb_data.reason = vhpiCbStartOfSimulation;
}

VhpiShutdownCbHdl::VhpiShutdownCbHdl(GpiImplInterface *impl) : VhpiCbHdl(impl) {
    cb_data.reason = vhpiCbEndOfSimulation;
}

VhpiTimedCbHdl::VhpiTimedCbHdl(GpiImplInterface *impl, uint64_t time)
    : VhpiCbHdl(impl) {
    vhpi_time.high = (uint32_t)(time >> 32);
    vhpi_time.low = (uint32_t)(time);

    cb_data.reason = vhpiCbAfterDelay;
    cb_data.time = &vhpi_time;
}

VhpiReadWriteCbHdl::VhpiReadWriteCbHdl(GpiImplInterface *impl)
    : VhpiCbHdl(impl) {
    cb_data.reason = vhpiCbRepLastKnownDeltaCycle;
    cb_data.time = &vhpi_time;
}

VhpiReadOnlyCbHdl::VhpiReadOnlyCbHdl(GpiImplInterface *impl) : VhpiCbHdl(impl) {
    cb_data.reason = vhpiCbRepEndOfTimeStep;
    cb_data.time = &vhpi_time;
}

VhpiNextPhaseCbHdl::VhpiNextPhaseCbHdl(GpiImplInterface *impl)
    : VhpiCbHdl(impl) {
    cb_data.reason = vhpiCbRepNextTimeStep;
    cb_data.time = &vhpi_time;
}
