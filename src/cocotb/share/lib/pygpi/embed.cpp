// Copyright cocotb contributors
// Copyright (c) 2013, 2018 Potential Ventures Ltd
// Copyright (c) 2013 SolarFlare Communications Inc
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

// Embed Python into the simulator using GPI

#include <Python.h>
#include <gpi.h>  // gpi_register_*

#include <cassert>
#include <cstdlib>
#include <cstring>
#include <string>

#include "../utils.hpp"      // DEFER
#include "./pygpi_priv.hpp"  // pygpi_logger_set_level, pygpi_logger_initialize, pygpi_logger_finalize, LOG_* macros, PYGPI_EXPORT

#if defined(_WIN32)
#include <windows.h>
#define sleep(n) Sleep(1000 * n)
#define getpid() GetCurrentProcessId()
#ifndef PATH_MAX
#define PATH_MAX MAX_PATH
#endif
#else
#include <unistd.h>
#endif

static bool python_init_called = 0;
static bool embed_init_called = 0;

static wchar_t progname[] = L"cocotb";
static wchar_t *argv[] = {progname};

static int get_interpreter_path(wchar_t *path, size_t path_size) {
    const char *path_c = getenv("PYGPI_PYTHON_BIN");
    if (!path_c) {
        // LCOV_EXCL_START
        PYGPI_LOG_ERROR(
            "PYGPI_PYTHON_BIN variable not set. Can't initialize Python "
            "interpreter!");
        return -1;
        // LCOV_EXCL_STOP
    }

    auto path_temp = Py_DecodeLocale(path_c, NULL);
    if (path_temp == NULL) {
        // LCOV_EXCL_START
        PYGPI_LOG_ERROR(
            "Unable to set Python Program Name. "
            "Decoding error in Python executable path.");
        PYGPI_LOG_INFO("Python executable path: %s", path_c);
        return -1;
        // LCOV_EXCL_STOP
    }
    DEFER(PyMem_RawFree(path_temp));

    wcsncpy(path, path_temp, path_size / sizeof(wchar_t));
    if (path[(path_size / sizeof(wchar_t)) - 1]) {
        // LCOV_EXCL_START
        PYGPI_LOG_ERROR(
            "Unable to set Python Program Name. Path to interpreter too long");
        PYGPI_LOG_INFO("Python executable path: %s", path_c);
        return -1;
        // LCOV_EXCL_STOP
    }

    return 0;
}

static void pygpi_init_debug() {
    char *debug_env = getenv("PYGPI_DEBUG");
    if (debug_env) {
        std::string pygpi_debug = debug_env;
        // If it's explicitly set to 0, don't enable
        if (pygpi_debug != "0") {
            pygpi_debug_enabled = 1;
            python_context_tracing_enabled = 1;
        }
    }
}

static int start_of_sim_time(void *);
static void end_of_sim_time(void *);
static void finalize(void *);

extern "C" PYGPI_EXPORT void initialize(void) {
    pygpi_init_debug();
    pygpi_logging_initialize();

    PYGPI_LOG_TRACE("GPI Init => [ PYGPI Init ]");
    DEFER(PYGPI_LOG_TRACE("[ PYGPI Init ] => GPI Init"));

    if (python_init_called) {
        // LCOV_EXCL_START
        PYGPI_LOG_ERROR("PyGPI library initialized again!");
        return;
        // LCOV_EXCL_STOP
    }
    python_init_called = 1;

    // must set program name to Python executable before initialization, so
    // initialization can determine path from executable

    static wchar_t interpreter_path[PATH_MAX], sys_executable[PATH_MAX];

    if (get_interpreter_path(interpreter_path, sizeof(interpreter_path))) {
        // LCOV_EXCL_START
        return;
        // LCOV_EXCL_STOP
    }
    PYGPI_LOG_INFO("Using Python %s interpreter at %ls", PY_VERSION,
                   interpreter_path);

    /* Use the new Python Initialization Configuration from Python 3.8. */
    PyConfig config;
    PyStatus status;

    PyConfig_InitPythonConfig(&config);
    DEFER(PyConfig_Clear(&config));

    PyConfig_SetString(&config, &config.executable, interpreter_path);

    status = PyConfig_SetArgv(&config, 1, argv);
    if (PyStatus_Exception(status)) {
        // LCOV_EXCL_START
        PYGPI_LOG_ERROR("Failed to set ARGV during the Python initialization");
        if (status.err_msg != NULL) {
            PYGPI_LOG_ERROR("\terror: %s", status.err_msg);
        }
        if (status.func != NULL) {
            PYGPI_LOG_ERROR("\tfunction: %s", status.func);
        }
        return;
        // LCOV_EXCL_STOP
    }

    status = Py_InitializeFromConfig(&config);
    if (PyStatus_Exception(status)) {
        // LCOV_EXCL_START
        PYGPI_LOG_ERROR("Failed to initialize Python");
        if (status.err_msg != NULL) {
            PYGPI_LOG_ERROR("\terror: %s", status.err_msg);
        }
        if (status.func != NULL) {
            PYGPI_LOG_ERROR("\tfunction: %s", status.func);
        }
        return;
        // LCOV_EXCL_STOP
    }

    /* Sanity check: make sure sys.executable was initialized to
     * interpreter_path. */
    PyObject *sys_executable_obj = PySys_GetObject("executable");
    if (sys_executable_obj == NULL) {
        // LCOV_EXCL_START
        PYGPI_LOG_ERROR("Failed to load sys.executable");
        // LCOV_EXCL_STOP
    } else if (PyUnicode_AsWideChar(sys_executable_obj, sys_executable,
                                    sizeof(sys_executable)) == -1) {
        // LCOV_EXCL_START
        PYGPI_LOG_ERROR("Failed to convert sys.executable to wide string");
        // LCOV_EXCL_STOP
    } else if (wcscmp(interpreter_path, sys_executable) != 0) {
        // LCOV_EXCL_START
        PYGPI_LOG_ERROR(
            "Unexpected sys.executable value (expected '%ls', got '%ls')",
            interpreter_path, sys_executable);
        // LCOV_EXCL_STOP
    }

    gpi_register_start_of_sim_time_callback(start_of_sim_time, nullptr);
    gpi_register_end_of_sim_time_callback(end_of_sim_time, nullptr);
    gpi_register_finalize_callback(finalize, nullptr);

    /* Before returning we check if the user wants pause the simulator thread
       such that they can attach */
    const char *pause = getenv("COCOTB_ATTACH");
    if (pause) {
        unsigned long sleep_time = strtoul(pause, NULL, 10);
        /* This should check for out-of-range parses which returns ULONG_MAX and
           sets errno, as well as correct parses that would be sliced by the
           narrowing cast */
        if (errno == ERANGE || sleep_time >= UINT_MAX) {
            // LCOV_EXCL_START
            PYGPI_LOG_ERROR(
                "COCOTB_ATTACH only needs to be set to ~30 seconds");
            return;
            // LCOV_EXCL_STOP
        }
        if ((errno != 0 && sleep_time == 0) || (sleep_time <= 0)) {
            // LCOV_EXCL_START
            PYGPI_LOG_ERROR(
                "COCOTB_ATTACH must be set to an integer base 10 or omitted");
            return;
            // LCOV_EXCL_STOP
        }

        PYGPI_LOG_INFO(
            "Waiting for %lu seconds - attach to PID %d with your debugger",
            sleep_time, getpid());
        sleep((unsigned int)sleep_time);
    }
}

static void finalize(void *) {
    PYGPI_LOG_TRACE("GPI Finalize => [ PYGPI Finalize ]");
    DEFER(PYGPI_LOG_TRACE("[ PYGPI Finalize ] => GPI Finalize"));
    // If initialization fails, this may be called twice:
    // Before the initial callback returns and in the final callback.
    // So we check if Python is still initialized before doing cleanup.
    if (Py_IsInitialized()) {
        c_to_python();
        PyGILState_Ensure();  // Don't save state as we are calling Py_Finalize
        Py_XDECREF(pEventFn);
        pEventFn = NULL;
        pygpi_logging_finalize();
        Py_Finalize();
        python_to_c();
    }
}

static int start_of_sim_time(void *) {
    PYGPI_LOG_TRACE("GPI Start Sim => [ PYGPI Start ]");
    DEFER(PYGPI_LOG_TRACE("[ PYGPI Start ] => GPI Start Sim"));

    // Check that we are not already initialized
    if (embed_init_called) {
        // LCOV_EXCL_START
        PYGPI_LOG_ERROR("PyGPI library initialized again!");
        return -1;
        // LCOV_EXCL_STOP
    }
    embed_init_called = 1;

    // Ensure that the current thread is ready to call the Python C API
    auto gstate = PyGILState_Ensure();
    DEFER(PyGILState_Release(gstate));

    c_to_python();
    DEFER(python_to_c());

    auto entry_utility_module = PyImport_ImportModule("pygpi.entry");
    if (!entry_utility_module) {
        // LCOV_EXCL_START
        PyErr_Print();
        return -1;
        // LCOV_EXCL_STOP
    }
    DEFER(Py_DECREF(entry_utility_module));

    auto cocotb_retval =
        PyObject_CallMethod(entry_utility_module, "load_entry", nullptr);
    if (!cocotb_retval) {
        // Printing a SystemExit calls exit(1), which we don't want.
        if (!PyErr_ExceptionMatches(PyExc_SystemExit)) {
            PyErr_Print();
        }
        // Clear error so re-entering Python doesn't fail.
        PyErr_Clear();
        return -1;
    }
    Py_DECREF(cocotb_retval);

    return 0;
}

static void end_of_sim_time(void *) {
    PYGPI_LOG_TRACE("GPI End Sim => [ PYGPI End ]");
    DEFER(PYGPI_LOG_TRACE("[ PYGPI End ] => GPI End Sim"));

    /* Indicate to the upper layer that a sim event occurred */

    if (pEventFn) {
        PyGILState_STATE gstate;
        c_to_python();
        gstate = PyGILState_Ensure();

        PyObject *pValue = PyObject_CallNoArgs(pEventFn);
        if (pValue == NULL) {
            // Printing a SystemExit calls exit(1), which we don't want.
            if (!PyErr_ExceptionMatches(PyExc_SystemExit)) {
                PyErr_Print();
            }
            // Clear error so re-entering Python doesn't fail.
            PyErr_Clear();
            PYGPI_LOG_ERROR("Passing event to upper layer failed");
        }
        Py_XDECREF(pValue);
        PyGILState_Release(gstate);
        python_to_c();
    }
}
