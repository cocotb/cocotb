// Copyright cocotb contributors
// Copyright (c) 2013 Potential Ventures Ltd
// Copyright (c) 2013 SolarFlare Communications Inc
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include "./dynload.hpp"

#include <cstdio>

#ifdef _WIN32
#include <windows.h>
#else
#include <dlfcn.h>
#endif

void *utils_dyn_open(const char *lib_name) {
    void *ret = NULL;
#ifdef _WIN32
    SetErrorMode(0);
    ret = static_cast<void *>(LoadLibrary(lib_name));
    if (!ret) {
        LPSTR msg_ptr;
        if (FormatMessageA(
                FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_ALLOCATE_BUFFER,
                NULL, GetLastError(),
                MAKELANGID(LANG_NEUTRAL, SUBLANG_SYS_DEFAULT), (LPSTR)&msg_ptr,
                255, NULL)) {
            fprintf(stderr, "[%s:%d]: Unable to open lib '%s'%s%s", __FILE__,
                    __LINE__, lib_name, ": ", msg_ptr);
            LocalFree(msg_ptr);
        } else {
            fprintf(stderr, "[%s:%d]: Unable to open lib '%s'%s%s", __FILE__,
                    __LINE__, lib_name, "", "");
        }
    }
#else
    /* Clear status */
    dlerror();

    ret = dlopen(lib_name, RTLD_LAZY | RTLD_GLOBAL);
    if (!ret) {
        fprintf(stderr, "[%s:%d]: Unable to open lib '%s': %s\n", __FILE__,
                __LINE__, lib_name, dlerror());
    }
#endif
    return ret;
}

void *utils_dyn_sym(void *handle, const char *sym_name) {
    void *entry_point;
#ifdef _WIN32
    entry_point = reinterpret_cast<void *>(
        GetProcAddress(static_cast<HMODULE>(handle), sym_name));
    if (!entry_point) {
        LPSTR msg_ptr;
        if (FormatMessageA(
                FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_ALLOCATE_BUFFER,
                NULL, GetLastError(),
                MAKELANGID(LANG_NEUTRAL, SUBLANG_SYS_DEFAULT), (LPSTR)&msg_ptr,
                255, NULL)) {
            fprintf(stderr, "[%s:%d]: Unable to find symbol '%s'%s%s", __FILE__,
                    __LINE__, sym_name, ": ", msg_ptr);
            LocalFree(msg_ptr);
        } else {
            fprintf(stderr, "[%s:%d]: Unable to find symbol '%s'%s%s", __FILE__,
                    __LINE__, sym_name, "", "");
        }
    }
#else
    entry_point = dlsym(handle, sym_name);
    if (!entry_point) {
        fprintf(stderr, "[%s:%d]: Unable to find symbol '%s': %s\n", __FILE__,
                __LINE__, sym_name, dlerror());
    }
#endif
    return entry_point;
}
