// Copyright cocotb contributors
// Copyright (c) 2013 Potential Ventures Ltd
// Copyright (c) 2013 SolarFlare Communications Inc
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include <cocotb_utils.h>
#include <gpi_logging.h>
#include <stdlib.h>

#ifdef _WIN32
#include <windows.h>
#else
#include <dlfcn.h>
#endif

// Tracks if we are in the context of Python or Simulator
int is_python_context = 0;

extern "C" void *utils_dyn_open(const char *lib_name) {
    void *ret = NULL;
#ifdef _WIN32
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
#ifdef _WIN32
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
