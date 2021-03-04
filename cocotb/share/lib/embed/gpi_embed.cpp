/******************************************************************************
 * Copyright (c) 2013, 2018 Potential Ventures Ltd
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

// Embed Python into the simulator using GPI

#include <Python.h>
#include <cocotb_utils.h>
#include <exports.h>
#include <gpi.h>          // gpi_event_t
#include <gpi_logging.h>  // LOG_* macros
#include <py_gpi_logging.h>  // py_gpi_logger_set_level, py_gpi_logger_initialize, py_gpi_logger_finalize

#include <cassert>

#include "locale.h"

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
static PyThreadState *gtstate = NULL;

static wchar_t progname[] = L"cocotb";
static wchar_t *argv[] = {progname};

#if defined(_WIN32)
#if defined(__MINGW32__) || defined(__CYGWIN32__)
const char *PYTHON_INTERPRETER_PATH = "/Scripts/python";
#else
const char *PYTHON_INTERPRETER_PATH = "\\Scripts\\python";
#endif
#else
const char *PYTHON_INTERPRETER_PATH = "/bin/python";
#endif

static PyObject *pEventFn = NULL;

static void set_program_name_in_venv(void) {
    static char venv_path[PATH_MAX];
    static wchar_t venv_path_w[PATH_MAX];

    const char *venv_path_home = getenv("VIRTUAL_ENV");
    if (!venv_path_home) {
        LOG_INFO(
            "Did not detect Python virtual environment. Using system-wide "
            "Python interpreter");
        return;
    }

    strncpy(venv_path, venv_path_home, sizeof(venv_path) - 1);
    if (venv_path[sizeof(venv_path) - 1]) {
        LOG_ERROR(
            "Unable to set Python Program Name using virtual environment. Path "
            "to virtual environment too long");
        return;
    }

    strncat(venv_path, PYTHON_INTERPRETER_PATH,
            sizeof(venv_path) - strlen(venv_path) - 1);
    if (venv_path[sizeof(venv_path) - 1]) {
        LOG_ERROR(
            "Unable to set Python Program Name using virtual environment. Path "
            "to interpreter too long");
        return;
    }

    wcsncpy(venv_path_w, Py_DecodeLocale(venv_path, NULL),
            sizeof(venv_path_w) / sizeof(wchar_t));

    if (venv_path_w[(sizeof(venv_path_w) / sizeof(wchar_t)) - 1]) {
        LOG_ERROR(
            "Unable to set Python Program Name using virtual environment. Path "
            "to interpreter too long");
        return;
    }

    LOG_INFO("Using Python virtual environment interpreter at %ls",
             venv_path_w);
    Py_SetProgramName(venv_path_w);
}

/**
 * @name    Initialize the Python interpreter
 * @brief   Create and initialize the Python interpreter
 * @ingroup python_c_api
 *
 * GILState before calling: N/A
 *
 * GILState after calling: released
 *
 * Stores the thread state for cocotb in static variable gtstate
 */

extern "C" COCOTB_EXPORT void _embed_init_python(void) {
    assert(!gtstate);  // this function should not be called twice

    to_python();
    set_program_name_in_venv();
    Py_Initialize(); /* Initialize the interpreter */
    PySys_SetArgvEx(1, argv, 0);

    /* Swap out and return current thread state and release the GIL */
    gtstate = PyEval_SaveThread();
    to_simulator();

    /* Before returning we check if the user wants pause the simulator thread
       such that they can attach */
    const char *pause = getenv("COCOTB_ATTACH");
    if (pause) {
        unsigned long sleep_time = strtoul(pause, NULL, 10);
        /* This should check for out-of-range parses which returns ULONG_MAX and
           sets errno, as well as correct parses that would be sliced by the
           narrowing cast */
        if (errno == ERANGE || sleep_time >= UINT_MAX) {
            LOG_ERROR("COCOTB_ATTACH only needs to be set to ~30 seconds");
            return;
        }
        if ((errno != 0 && sleep_time == 0) || (sleep_time <= 0)) {
            LOG_ERROR(
                "COCOTB_ATTACH must be set to an integer base 10 or omitted");
            return;
        }

        LOG_ERROR(
            "Waiting for %lu seconds - attach to PID %d with your debugger",
            sleep_time, getpid());
        sleep((unsigned int)sleep_time);
    }
}

/**
 * @name    Simulator cleanup
 * @brief   Called by the simulator on shutdown.
 * @ingroup python_c_api
 *
 * GILState before calling: Not held
 *
 * GILState after calling: Not held
 *
 * Makes one call to PyGILState_Ensure and one call to Py_Finalize.
 *
 * Cleans up reference counts for Python objects and calls Py_Finalize function.
 */
extern "C" COCOTB_EXPORT void _embed_sim_cleanup(void) {
    // If initialization fails, this may be called twice:
    // Before the initial callback returns and in the final callback.
    // So we check if Python is still initialized before doing cleanup.
    if (Py_IsInitialized()) {
        to_python();
        PyGILState_Ensure();  // Don't save state as we are calling Py_Finalize
        Py_DecRef(pEventFn);
        pEventFn = NULL;
        py_gpi_logger_finalize();
        Py_Finalize();
        to_simulator();
    }
}

/**
 * @name    Initialization
 * @brief   Called by the simulator on initialization. Load cocotb Python module
 * @ingroup python_c_api
 *
 * GILState before calling: Not held
 *
 * GILState after calling: Not held
 *
 * Makes one call to PyGILState_Ensure and one call to PyGILState_Release
 *
 * Loads the Python module called cocotb and calls the _initialise_testbench
 * function
 */

static int get_module_ref(const char *modname, PyObject **mod) {
    PyObject *pModule = PyImport_ImportModule(modname);

    if (pModule == NULL) {
        // LCOV_EXCL_START
        PyErr_Print();
        LOG_ERROR("Failed to load Python module \"%s\"", modname);
        return -1;
        // LCOV_EXCL_STOP
    }

    *mod = pModule;
    return 0;
}

extern "C" COCOTB_EXPORT int _embed_sim_init(int argc,
                                             char const *const *argv) {
    int i;
    int ret = 0;

    /* Check that we are not already initialized */
    if (pEventFn) return ret;

    PyObject *cocotb_module, *cocotb_init, *cocotb_retval;
    PyObject *cocotb_log_module = NULL;
    PyObject *log_func;
    PyObject *filter_func;
    PyObject *argv_list;

    cocotb_module = NULL;

    // Ensure that the current thread is ready to call the Python C API
    PyGILState_STATE gstate = PyGILState_Ensure();
    to_python();

    if (get_module_ref("cocotb", &cocotb_module)) {
        // LCOV_EXCL_START
        goto cleanup;
        // LCOV_EXCL_STOP
    }

    LOG_INFO("Python interpreter initialized and cocotb loaded!");

    if (get_module_ref("cocotb.log", &cocotb_log_module)) {
        // LCOV_EXCL_START
        goto cleanup;
        // LCOV_EXCL_STOP
    }

    // Obtain the function to use when logging from C code
    log_func = PyObject_GetAttrString(cocotb_log_module,
                                      "_log_from_c");  // New reference
    if (log_func == NULL) {
        // LCOV_EXCL_START
        PyErr_Print();
        LOG_ERROR("Failed to get the _log_from_c function");
        goto cleanup;
        // LCOV_EXCL_STOP
    }

    // Obtain the function to check whether to call log function
    filter_func = PyObject_GetAttrString(cocotb_log_module,
                                         "_filter_from_c");  // New reference
    if (filter_func == NULL) {
        // LCOV_EXCL_START
        Py_DECREF(log_func);
        PyErr_Print();
        LOG_ERROR("Failed to get the _filter_from_c method");
        goto cleanup;
        // LCOV_EXCL_STOP
    }

    py_gpi_logger_initialize(
        log_func, filter_func);  // Note: This function steals references to
                                 // log_func and filter_func.

    pEventFn =
        PyObject_GetAttrString(cocotb_module, "_sim_event");  // New reference
    if (pEventFn == NULL) {
        // LCOV_EXCL_START
        PyErr_Print();
        LOG_ERROR("Failed to get the _sim_event method");
        goto cleanup;
        // LCOV_EXCL_STOP
    }

    cocotb_init = PyObject_GetAttrString(
        cocotb_module, "_initialise_testbench");  // New reference
    if (cocotb_init == NULL) {
        // LCOV_EXCL_START
        PyErr_Print();
        LOG_ERROR("Failed to get the _initialise_testbench method");
        goto cleanup;
        // LCOV_EXCL_STOP
    }

    // Build argv for cocotb module
    argv_list = PyList_New(argc);  // New reference
    if (argv_list == NULL) {
        // LCOV_EXCL_START
        PyErr_Print();
        LOG_ERROR("Unable to create argv list");
        goto cleanup;
        // LCOV_EXCL_STOP
    }
    for (i = 0; i < argc; i++) {
        // Decode, embedding non-decodable bytes using PEP-383. This can only
        // fail with MemoryError or similar.
        PyObject *argv_item = PyUnicode_DecodeLocale(
            argv[i], "surrogateescape");  // New reference
        if (argv_item == NULL) {
            // LCOV_EXCL_START
            PyErr_Print();
            LOG_ERROR(
                "Unable to convert command line argument %d to Unicode string.",
                i);
            Py_DECREF(argv_list);
            goto cleanup;
            // LCOV_EXCL_STOP
        }
        PyList_SET_ITEM(argv_list, i, argv_item);  // Note: This function steals
                                                   // the reference to argv_item
    }

    cocotb_retval = PyObject_CallFunctionObjArgs(cocotb_init, argv_list, NULL);
    Py_DECREF(argv_list);
    Py_DECREF(cocotb_init);

    if (cocotb_retval != NULL) {
        LOG_DEBUG("_initialise_testbench successful");
        Py_DECREF(cocotb_retval);
    } else {
        // LCOV_EXCL_START
        PyErr_Print();
        LOG_ERROR("cocotb initialization failed - exiting");
        goto cleanup;
        // LCOV_EXCL_STOP
    }

    goto ok;

cleanup:
    ret = -1;
ok:
    Py_XDECREF(cocotb_module);
    Py_XDECREF(cocotb_log_module);

    PyGILState_Release(gstate);
    to_simulator();

    return ret;
}

extern "C" COCOTB_EXPORT void _embed_sim_event(gpi_event_t level,
                                               const char *msg) {
    /* Indicate to the upper layer that a sim event occurred */

    if (pEventFn) {
        PyGILState_STATE gstate;
        to_python();
        gstate = PyGILState_Ensure();

        if (msg == NULL) {
            msg = "No message provided";
        }

        PyObject *pValue = PyObject_CallFunction(pEventFn, "ls", level, msg);
        if (pValue == NULL) {
            PyErr_Print();
            LOG_ERROR("Passing event to upper layer failed");
        }
        Py_XDECREF(pValue);
        PyGILState_Release(gstate);
        to_simulator();
    }
}
