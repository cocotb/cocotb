/******************************************************************************
 * Copyright (c) 2015/16 Potential Ventures Ltd
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *    * Redistributions of source code must retain the above copyright
 *      notice, this list of conditions and the following disclaimer.
 *    * Redistributions in binary form must reproduce the above copyright
 *      notice, this list of conditions and the following disclaimer in the
 *      documentation and/or other materials provided with the distribution.
 *    * Neither the name of Potential Ventures Ltd
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

#include <limits>

#include "FliImpl.h"
#include "_vendor/fli/mti.h"
#include "_vendor/tcl/tcl.h"

/**
 * @name    cleanup callback
 * @brief   Called while unwinding after a GPI callback
 *
 * We keep the process but desensitize it
 *
 * NB: need a way to determine if should leave it sensitized...
 *
 */
int FliProcessCbHdl::cleanup_callback() {
    if (get_call_state() == GPI_PRIMED) {
        mti_Desensitize(m_proc_hdl);
        set_call_state(GPI_DELETE);
    }
    return 0;
}

FliTimedCbHdl::FliTimedCbHdl(GpiImplInterface* impl, uint64_t time)
    : GpiCbHdl(impl), FliProcessCbHdl(impl), m_time(time) {
    m_proc_hdl = mti_CreateProcessWithPriority(NULL, handle_fli_callback,
                                               (void*)this, MTI_PROC_IMMEDIATE);
}

int FliTimedCbHdl::arm_callback() {
#if defined(__LP64__) || defined(_WIN64)
    mti_ScheduleWakeup64(m_proc_hdl, static_cast<mtiTime64T>(m_time));
#else
    mtiTime64T m_time_union_ps;
    MTI_TIME64_ASGN(m_time_union_ps, (mtiInt32T)((m_time) >> 32),
                    (mtiUInt32T)(m_time));
    mti_ScheduleWakeup64(m_proc_hdl, m_time_union_ps);
#endif
    set_call_state(GPI_PRIMED);
    return 0;
}

int FliTimedCbHdl::cleanup_callback() {
    switch (get_call_state()) {
        case GPI_PRIMED:
            /* Issue #188: Work around for modelsim that is harmless to othes
               too, we tag the time as delete, let it fire then do not pass up
               */
            LOG_DEBUG("Not removing PRIMED timer %p", m_time);
            set_call_state(GPI_DELETE);
            return 0;
        case GPI_CALL:
            LOG_DEBUG("Not removing CALL timer yet %p", m_time);
            set_call_state(GPI_DELETE);
            return 0;
        case GPI_DELETE:
            LOG_DEBUG("Removing Postponed DELETE timer %p", m_time);
            break;
        default:
            break;
    }
    FliProcessCbHdl::cleanup_callback();
    // put Timer back on cache instead of deleting
    FliImpl* impl = (FliImpl*)m_impl;
    impl->cache.put_timer(this);
    return 0;
}

int FliSignalCbHdl::arm_callback() {
    if (NULL == m_proc_hdl) {
        LOG_DEBUG("Creating a new process to sensitise to signal %s",
                  mti_GetSignalName(m_sig_hdl));
        m_proc_hdl = mti_CreateProcess(NULL, handle_fli_callback, (void*)this);
    }

    if (get_call_state() != GPI_PRIMED) {
        mti_Sensitize(m_proc_hdl, m_sig_hdl, MTI_EVENT);
        set_call_state(GPI_PRIMED);
    }
    return 0;
}

int FliSimPhaseCbHdl::arm_callback() {
    if (NULL == m_proc_hdl) {
        LOG_DEBUG("Creating a new process to sensitise with priority %d",
                  m_priority);
        m_proc_hdl = mti_CreateProcessWithPriority(NULL, handle_fli_callback,
                                                   (void*)this, m_priority);
    }

    if (get_call_state() != GPI_PRIMED) {
        mti_ScheduleWakeup(m_proc_hdl, 0);
        set_call_state(GPI_PRIMED);
    }
    return 0;
}

FliSignalCbHdl::FliSignalCbHdl(GpiImplInterface* impl, FliSignalObjHdl* sig_hdl,
                               int edge)
    : GpiCbHdl(impl),
      FliProcessCbHdl(impl),
      GpiValueCbHdl(impl, sig_hdl, edge) {
    m_sig_hdl = m_signal->get_handle<mtiSignalIdT>();
}

int FliStartupCbHdl::arm_callback() {
    mti_AddLoadDoneCB(handle_fli_callback, (void*)this);
    set_call_state(GPI_PRIMED);

    return 0;
}

static std::vector<std::string> get_argv() {
    /* Necessary to implement PLUSARGS
       There is no function available on the FLI to obtain argc+argv directly
       from the simulator. To work around this we use the TCL interpreter that
       ships with Questa, some TCL commands, and the TCL variable `argv` to
       obtain the simulator argc+argv.
    */
    std::vector<std::string> argv;

    // obtain a reference to TCL interpreter
    Tcl_Interp* interp = reinterpret_cast<Tcl_Interp*>(mti_Interp());

    // get argv TCL variable
    if (mti_Cmd("return -level 0 $argv") != TCL_OK) {
        const char* errmsg = Tcl_GetStringResult(interp);
        LOG_WARN("Failed to get reference to argv: %s", errmsg);
        Tcl_ResetResult(interp);
        return argv;
    }
    Tcl_Obj* result = Tcl_GetObjResult(interp);
    Tcl_IncrRefCount(result);
    Tcl_ResetResult(interp);

    // split TCL list into length and element array
    int argc;
    Tcl_Obj** tcl_argv;
    if (Tcl_ListObjGetElements(interp, result, &argc, &tcl_argv) != TCL_OK) {
        const char* errmsg = Tcl_GetStringResult(interp);
        LOG_WARN("Failed to get argv elements: %s", errmsg);
        Tcl_DecrRefCount(result);
        Tcl_ResetResult(interp);
        return argv;
    }
    Tcl_ResetResult(interp);

    // get each argv arg and copy into internal storage
    for (int i = 0; i < argc; i++) {
        const char* arg = Tcl_GetString(tcl_argv[i]);
        argv.push_back(arg);
    }
    Tcl_DecrRefCount(result);

    return argv;
}

int FliStartupCbHdl::run_callback() {
    std::vector<std::string> const argv_storage = get_argv();
    std::vector<const char*> argv_cstr;
    for (const auto& arg : argv_storage) {
        argv_cstr.push_back(arg.c_str());
    }
    int argc = static_cast<int>(argv_storage.size());
    const char** argv = argv_cstr.data();

    gpi_embed_init(argc, argv);

    return 0;
}

int FliShutdownCbHdl::arm_callback() {
    mti_AddQuitCB(handle_fli_callback, (void*)this);
    set_call_state(GPI_PRIMED);

    return 0;
}

int FliShutdownCbHdl::run_callback() {
    gpi_embed_end();

    return 0;
}
