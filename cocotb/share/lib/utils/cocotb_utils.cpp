/******************************************************************************
 * Copyright (c) 2013 Potential Ventures Ltd
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
 *AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 *IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
 * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 ******************************************************************************/

#include <cocotb_utils.h>
#include <gpi_logging.h>
#include <stdlib.h>

#if defined(__linux__) || defined(__APPLE__)
#include <dlfcn.h>
#else
#include <windows.h>
#endif

// Tracks if we are in the context of Python or Simulator
int is_python_context = 0;

extern "C" void *utils_dyn_open(const char *lib_name) {
    void *ret = NULL;
#if !defined(__linux__) && !defined(__APPLE__)
    SetErrorMode(0);
    ret = static_cast<void *>(LoadLibrary(lib_name));
    if (!ret) {
        const char *log_fmt = "Unable to open lib %s%s%s";
        LPSTR msg_ptr;
        if (FormatMessageA(
                FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_ALLOCATE_BUFFER,
                NULL, GetLastError(),
                MAKELANGID(LANG_NEUTRAL, SUBLANG_SYS_DEFAULT), (LPSTR)&msg_ptr,
                255, NULL)) {
            LOG_ERROR(log_fmt, lib_name, ": ", msg_ptr);
            LocalFree(msg_ptr);
        } else {
            LOG_ERROR(log_fmt, lib_name, "", "");
        }
    }
#else
    /* Clear status */
    dlerror();

    ret = dlopen(lib_name, RTLD_LAZY | RTLD_GLOBAL);
    if (!ret) {
        LOG_ERROR("Unable to open lib %s: %s", lib_name, dlerror());
    }
#endif
    return ret;
}

extern "C" void *utils_dyn_sym(void *handle, const char *sym_name) {
    void *entry_point;
#if !defined(__linux__) && !defined(__APPLE__)
    entry_point = reinterpret_cast<void *>(
        GetProcAddress(static_cast<HMODULE>(handle), sym_name));
    if (!entry_point) {
        const char *log_fmt = "Unable to find symbol %s%s%s";
        LPSTR msg_ptr;
        if (FormatMessageA(
                FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_ALLOCATE_BUFFER,
                NULL, GetLastError(),
                MAKELANGID(LANG_NEUTRAL, SUBLANG_SYS_DEFAULT), (LPSTR)&msg_ptr,
                255, NULL)) {
            LOG_ERROR(log_fmt, sym_name, ": ", msg_ptr);
            LocalFree(msg_ptr);
        } else {
            LOG_ERROR(log_fmt, sym_name, "", "");
        }
    }
#else
    entry_point = dlsym(handle, sym_name);
    if (!entry_point) {
        LOG_ERROR("Unable to find symbol %s: %s", sym_name, dlerror());
    }
#endif
    return entry_point;
}
