// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include <cocotb_utils.h>  // xstr, utils_dyn_open, utils_dyn_sym
#include <embed.h>
#include <gpi.h>  // gpi_event_t

#include <cstdlib>  // getenv
#ifdef _WIN32
#include <windows.h>  // Win32 API for loading the embed impl library

#include <string>  // string
#endif

#ifndef PYTHON_LIB
#error "Name of Python library required"
#else
#define PYTHON_LIB_STR xstr(PYTHON_LIB)
#endif

#ifndef EMBED_IMPL_LIB
#error "Name of embed implementation library required"
#else
#define EMBED_IMPL_LIB_STR xstr(EMBED_IMPL_LIB)
#endif

static void (*_embed_init_python)();
static void (*_embed_sim_cleanup)();
static int (*_embed_sim_init)(int argc, char const *const *argv);
static void (*_embed_sim_event)(const char *msg);

static bool init_failed = false;

#ifdef _WIN32
static ACTCTX act_ctx = {
    /* cbSize */ sizeof(ACTCTX),
    /* dwFlags */ ACTCTX_FLAG_HMODULE_VALID | ACTCTX_FLAG_RESOURCE_NAME_VALID,
    /* lpSource */ NULL,
    /* wProcessorArchitecture */ 0,
    /* wLangId */ 0,
    /* lpAssemblyDirectory */ NULL,
    /* lpResourceName */ MAKEINTRESOURCE(1000),
    /* lpApplicationName */ NULL,
    /* hModule */ 0};

BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID) {
    if (fdwReason == DLL_PROCESS_ATTACH) {
        act_ctx.hModule = hinstDLL;
    }

    return TRUE;
}
#endif

extern "C" void embed_init_python(void) {
    // preload python library
    char const *libpython_path = getenv("LIBPYTHON_LOC");
    if (!libpython_path) {
        // default to libpythonX.X.so
        libpython_path = PYTHON_LIB_STR;
    }
    auto loaded = utils_dyn_open(libpython_path);
    if (!loaded) {
        // LCOV_EXCL_START
        init_failed = true;
        return;
        // LCOV_EXCL_STOP
    }

#ifdef _WIN32
    if (!act_ctx.hModule) {
        // LCOV_EXCL_START
        init_failed = true;
        return;
        // LCOV_EXCL_STOP
    }

    HANDLE hact_ctx = CreateActCtx(&act_ctx);
    if (hact_ctx == INVALID_HANDLE_VALUE) {
        // LCOV_EXCL_START
        init_failed = true;
        return;
        // LCOV_EXCL_STOP
    }

    ULONG_PTR Cookie;
    if (!ActivateActCtx(hact_ctx, &Cookie)) {
        // LCOV_EXCL_START
        init_failed = true;
        return;
        // LCOV_EXCL_STOP
    }
#endif

    // load embed implementation library and functions
    void *embed_impl_lib_handle;
    if (!(embed_impl_lib_handle = utils_dyn_open(EMBED_IMPL_LIB_STR))) {
        // LCOV_EXCL_START
        init_failed = true;
        return;
        // LCOV_EXCL_STOP
    }
    if (!(_embed_init_python = reinterpret_cast<decltype(_embed_init_python)>(
              utils_dyn_sym(embed_impl_lib_handle, "_embed_init_python")))) {
        // LCOV_EXCL_START
        init_failed = true;
        return;
        // LCOV_EXCL_STOP
    }
    if (!(_embed_sim_cleanup = reinterpret_cast<decltype(_embed_sim_cleanup)>(
              utils_dyn_sym(embed_impl_lib_handle, "_embed_sim_cleanup")))) {
        // LCOV_EXCL_START
        init_failed = true;
        return;
        // LCOV_EXCL_STOP
    }
    if (!(_embed_sim_init = reinterpret_cast<decltype(_embed_sim_init)>(
              utils_dyn_sym(embed_impl_lib_handle, "_embed_sim_init")))) {
        // LCOV_EXCL_START
        init_failed = true;
        return;
        // LCOV_EXCL_STOP
    }
    if (!(_embed_sim_event = reinterpret_cast<decltype(_embed_sim_event)>(
              utils_dyn_sym(embed_impl_lib_handle, "_embed_sim_event")))) {
        // LCOV_EXCL_START
        init_failed = true;
        return;
        // LCOV_EXCL_STOP
    }

#ifdef _WIN32
    if (!DeactivateActCtx(0, Cookie)) {
        // LCOV_EXCL_START
        init_failed = true;
        return;
        // LCOV_EXCL_STOP
    }

    ReleaseActCtx(hact_ctx);
#endif

    // call to embed library impl
    _embed_init_python();
}

extern "C" void embed_sim_cleanup(void) {
    if (!init_failed) {
        _embed_sim_cleanup();
    }
}

extern "C" int embed_sim_init(int argc, char const *const *argv) {
    if (init_failed) {
        // LCOV_EXCL_START
        return -1;
        // LCOV_EXCL_STOP
    } else {
        return _embed_sim_init(argc, argv);
    }
}

extern "C" void embed_sim_event(const char *msg) {
    if (!init_failed) {
        _embed_sim_event(msg);
    }
}
