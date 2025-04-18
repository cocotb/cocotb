// Copyright cocotb contributors
// Copyright (c) 2015/16 Potential Ventures Ltd
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include <cstring>

#include "FliImpl.h"
#include "_vendor/fli/mti.h"

// Main re-entry point for callbacks from simulator
void handle_fli_callback(void* data) {
    gpi_to_user();

    // TODO Add why?
    fflush(stderr);

    FliCbHdl* cb_hdl = (FliCbHdl*)data;

    // LCOV_EXCL_START
    if (!cb_hdl) {
        LOG_CRITICAL("FLI: Callback data corrupted: ABORTING");
        gpi_embed_end();
        return;
    }
    // LCOV_EXCL_STOP

    if (cb_hdl->run()) {
        // sim failed, so call shutdown
        gpi_embed_end();
    }

    gpi_to_simulator();
}

int FliTimedCbHdl::arm() {
    // These are reused, so we need to reset m_removed.
    m_removed = false;
#if defined(__LP64__) || defined(_WIN64)
    mti_ScheduleWakeup64(m_proc_hdl, static_cast<mtiTime64T>(m_time));
#else
    mtiTime64T m_time_union_ps;
    MTI_TIME64_ASGN(m_time_union_ps, (mtiInt32T)((m_time) >> 32),
                    (mtiUInt32T)(m_time));
    mti_ScheduleWakeup64(m_proc_hdl, m_time_union_ps);
#endif
    return 0;
}

int FliTimedCbHdl::run() {
    int res = 0;
    if (!m_removed) {
        // Prevent the callback from calling up if it's been removed.
        res = m_cb_func(m_cb_data);
    }
    // Don't delete, but release back to the appropriate cache to be reused.
    release();
    return res;
}

int FliTimedCbHdl::remove() {
    // mti_ScheduleWakeup callbacks can't be cancelled, so we mark the callback
    // as removed and let it fire. When it fires, this flag prevents it from
    // calling up and then releases the callback back to the appropriate cache
    // to be reused.
    m_removed = true;
    return 0;
}

int FliSignalCbHdl::arm() {
    mti_Sensitize(m_proc_hdl, m_signal->get_handle<mtiSignalIdT>(), MTI_EVENT);
    return 0;
}

int FliSignalCbHdl::run() {
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

        // Don't delete, but desensitize the process from the signal change and
        // release back to the appropriate cache to be reused.
        mti_Desensitize(m_proc_hdl);
        release();
    }  // else don't remove and let it fire again.

    return res;
}

int FliSignalCbHdl::remove() {
    // Don't delete, but desensitize the process from the signal change and
    // release back to the appropriate cache to be reused.
    mti_Desensitize(m_proc_hdl);
    release();
    return 0;
}

int FliSimPhaseCbHdl::arm() {
    mti_ScheduleWakeup(m_proc_hdl, 0);
    m_removed = false;
    return 0;
}

int FliSimPhaseCbHdl::run() {
    int res = 0;
    if (!m_removed) {
        // Prevent the callback from calling up if it's been removed.
        res = m_cb_func(m_cb_data);
    }
    // Don't delete, but release back to the appropriate cache to be reused.
    release();
    return res;
}

int FliSimPhaseCbHdl::remove() {
    // mti_ScheduleWakeup callbacks can't be cancelled, so we mark the callback
    // as removed and let it fire. When it fires, this flag prevents it from
    // calling up and then releases the callback back to the appropriate cache
    // to be reused.
    m_removed = true;
    return 0;
}

void FliSignalCbHdl::release() {
    dynamic_cast<FliImpl*>(m_impl)->m_value_change_cache.release(this);
}

void FliTimedCbHdl::release() {
    dynamic_cast<FliImpl*>(m_impl)->m_timer_cache.release(this);
}

void FliReadOnlyCbHdl::release() {
    dynamic_cast<FliImpl*>(m_impl)->m_read_only_cache.release(this);
}

void FliReadWriteCbHdl::release() {
    dynamic_cast<FliImpl*>(m_impl)->m_read_write_cache.release(this);
}

void FliNextPhaseCbHdl::release() {
    dynamic_cast<FliImpl*>(m_impl)->m_next_phase_cache.release(this);
}

int FliStartupCbHdl::arm() {
    mti_AddLoadDoneCB(handle_fli_callback, (void*)this);
    return 0;
}

int FliStartupCbHdl::run() {
    int res = m_cb_func(m_cb_data);
    delete this;
    return res;
}

int FliStartupCbHdl::remove() {
    mti_RemoveLoadDoneCB(handle_fli_callback, (void*)this);
    delete this;
    return 0;
}

int FliShutdownCbHdl::arm() {
    mti_AddQuitCB(handle_fli_callback, (void*)this);
    return 0;
}

int FliShutdownCbHdl::run() {
    int res = m_cb_func(m_cb_data);
    delete this;
    return res;
}

int FliShutdownCbHdl::remove() {
    mti_RemoveQuitCB(handle_fli_callback, (void*)this);
    delete this;
    return 0;
}
