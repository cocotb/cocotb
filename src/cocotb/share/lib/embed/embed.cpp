// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include "embed.h"

#include <cstdlib>  // getenv

#include "../gpi/gpi_priv.h"  // utils_dyn_open, utils_dyn_sym
#include "gpi_logging.h"

#ifdef _WIN32
#include <windows.h>  // Win32 API for loading the embed impl library

#include <string>  // string
#endif

static void (*_embed_sim_init)();
static void (*_embed_sim_cleanup)();
static int (*_embed_init_python)(int argc, char const *const *argv);
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

extern "C" int embed_init_python(int argc, char const *const *argv) {
    // preload python library
    char const *libpython_path = getenv("LIBPYTHON_LOC");
    // LCOV_EXCL_START
    if (!libpython_path) {
        LOG_DEBUG("Missing required environment variable LIBPYTHON_LOC");
        init_failed = true;
        return -1;
    }
    // LCOV_EXCL_STOP

    auto loaded = utils_dyn_open(libpython_path);
    if (!loaded) {
        // LCOV_EXCL_START
        init_failed = true;
        return -1;
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

    char const *user_lib_path = getenv("GPI_USERS");
    // LCOV_EXCL_START
    if (!user_lib_path) {
        LOG_DEBUG("Missing required environment variable GPI_USERS");
        init_failed = true;
        return -1;
    }
    // LCOV_EXCL_STOP

    // load embed implementation library and functions
    void *embed_impl_lib_handle = utils_dyn_open(user_lib_path);
    if (!embed_impl_lib_handle) {
        // LCOV_EXCL_START
        init_failed = true;
        return -1;
        // LCOV_EXCL_STOP
    }
    if (!(_embed_init_python = reinterpret_cast<decltype(_embed_init_python)>(
              utils_dyn_sym(embed_impl_lib_handle, "_embed_init_python")))) {
        // LCOV_EXCL_START
        init_failed = true;
        return -1;
        // LCOV_EXCL_STOP
    }
    if (!(_embed_sim_cleanup = reinterpret_cast<decltype(_embed_sim_cleanup)>(
              utils_dyn_sym(embed_impl_lib_handle, "_embed_sim_cleanup")))) {
        // LCOV_EXCL_START
        init_failed = true;
        return -1;
        // LCOV_EXCL_STOP
    }
    if (!(_embed_sim_init = reinterpret_cast<decltype(_embed_sim_init)>(
              utils_dyn_sym(embed_impl_lib_handle, "_embed_sim_init")))) {
        // LCOV_EXCL_START
        init_failed = true;
        return -1;
        // LCOV_EXCL_STOP
    }
    if (!(_embed_sim_event = reinterpret_cast<decltype(_embed_sim_event)>(
              utils_dyn_sym(embed_impl_lib_handle, "_embed_sim_event")))) {
        // LCOV_EXCL_START
        init_failed = true;
        return -1;
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
    return _embed_init_python(argc, argv);
}

extern "C" void embed_sim_cleanup(void) {
    if (!init_failed) {
        _embed_sim_cleanup();
    }
}

extern "C" void embed_sim_init(void) {
    if (init_failed) {
        // LCOV_EXCL_START
        return;
        // LCOV_EXCL_STOP
    } else {
        _embed_sim_init();
    }
}

extern "C" void embed_sim_event(const char *msg) {
    if (!init_failed) {
        _embed_sim_event(msg);
    }
}
