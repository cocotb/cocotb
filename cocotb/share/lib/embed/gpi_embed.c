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
* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
* ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
* WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
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
#include "embed.h"
#include "../compat/python3_compat.h"
#include "locale.h"

#if defined(_WIN32)
#include <windows.h>
#define sleep(n) Sleep(1000 * n)
#ifndef PATH_MAX
#define PATH_MAX MAX_PATH
#endif
#endif
static PyThreadState *gtstate = NULL;

#if PY_MAJOR_VERSION >= 3
static wchar_t progname[] = L"cocotb";
static wchar_t *argv[] = { progname };
#else
static char progname[] = "cocotb";
static char *argv[] = { progname };
#endif

#if defined(_WIN32)
#if defined(__MINGW32__) || defined (__CYGWIN32__)
const char* PYTHON_INTERPRETER_PATH = "/Scripts/python";
#else
const char* PYTHON_INTERPRETER_PATH = "\\Scripts\\python";
#endif
#else
const char* PYTHON_INTERPRETER_PATH = "/bin/python";
#endif


static PyObject *pEventFn = NULL;


static void set_program_name_in_venv(void)
{
    static char venv_path[PATH_MAX];
#if PY_MAJOR_VERSION >= 3
    static wchar_t venv_path_w[PATH_MAX];
#endif

    const char *venv_path_home = getenv("VIRTUAL_ENV");
    if (!venv_path_home) {
        LOG_INFO("Did not detect Python virtual environment. Using system-wide Python interpreter");
        return;
    }

    strncpy(venv_path, venv_path_home, sizeof(venv_path));
    if (venv_path[sizeof(venv_path) - 1]) {
        LOG_ERROR("Unable to set Python Program Name using virtual environment. Path to virtual environment too long");
        return;
    }

    strncat(venv_path, PYTHON_INTERPRETER_PATH, sizeof(venv_path) - strlen(venv_path) - 1);
    if (venv_path[sizeof(venv_path) - 1]) {
        LOG_ERROR("Unable to set Python Program Name using virtual environment. Path to interpreter too long");
        return;
    }

#if PY_MAJOR_VERSION >= 3
    wcsncpy(venv_path_w, Py_DecodeLocale(venv_path, NULL), sizeof(venv_path_w)/sizeof(wchar_t));

    if (venv_path_w[(sizeof(venv_path_w)/sizeof(wchar_t)) - 1]) {
        LOG_ERROR("Unable to set Python Program Name using virtual environment. Path to interpreter too long");
        return;
    }

    LOG_INFO("Using Python virtual environment interpreter at %ls", venv_path_w);
    Py_SetProgramName(venv_path_w);
#else
    LOG_INFO("Using Python virtual environment interpreter at %s", venv_path);
    Py_SetProgramName(venv_path);
#endif
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

void embed_init_python(void)
{
    FENTER;

#ifndef PYTHON_SO_LIB
#error "Python version needs passing in with -DPYTHON_SO_VERSION=libpython<ver>.so"
#else
#define PY_SO_LIB xstr(PYTHON_SO_LIB)
#endif

    // Don't initialize Python if already running
    if (gtstate)
        return;

    void * lib_handle = utils_dyn_open(PY_SO_LIB);
    if (!lib_handle) {
        LOG_ERROR("Failed to find Python shared library\n");
    }

    to_python();
    set_program_name_in_venv();
    Py_Initialize();                    /* Initialize the interpreter */
    PySys_SetArgvEx(1, argv, 0);
    PyEval_InitThreads();               /* Create (and acquire) the interpreter lock */

    /* Swap out and return current thread state and release the GIL */
    gtstate = PyEval_SaveThread();
    to_simulator();

    /* Before returning we check if the user wants pause the simulator thread
       such that they can attach */
    const char *pause = getenv("COCOTB_ATTACH");
    if (pause) {
        long sleep_time = strtol(pause, NULL, 10);
        if (errno == ERANGE && (sleep_time == LONG_MAX || sleep_time == LONG_MIN)) {
            LOG_ERROR("COCOTB_ATTACH only needs to be set to ~30 seconds");
            goto out;
        }
        if ((errno != 0 && sleep_time == 0) ||
            (sleep_time <= 0)) {
            LOG_ERROR("COCOTB_ATTACH must be set to an integer base 10 or omitted");
            goto out;
        }

        LOG_ERROR("Waiting for %lu seconds - attach to PID %d with your debugger\n", sleep_time, getpid());
        sleep(sleep_time);
    }
out:
    FEXIT;
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
void embed_sim_cleanup(void)
{
    // If initialization fails, this may be called twice:
    // Before the initial callback returns and in the final callback.
    // So we check if Python is still initialized before doing cleanup.
    if (Py_IsInitialized()) {
        to_python();
        PyGILState_Ensure();    // Don't save state as we are calling Py_Finalize
        Py_DecRef(pEventFn);
        pEventFn = NULL;
        clear_log_handler();
        clear_log_filter();
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
 * Loads the Python module called cocotb and calls the _initialise_testbench function
 */

int get_module_ref(const char *modname, PyObject **mod)
{
    PyObject *pModule = PyImport_ImportModule(modname);

    if (pModule == NULL) {
        PyErr_Print();
        LOG_ERROR("Failed to load Python module \"%s\"\n", modname);
        return -1;
    }

    *mod = pModule;
    return 0;
}

int embed_sim_init(gpi_sim_info_t *info)
{
    FENTER

    int i;
    int ret = 0;

    /* Check that we are not already initialized */
    if (pEventFn)
        return ret;

    // Find the simulation root
    const char *dut = getenv("TOPLEVEL");

    if (dut != NULL) {
        if (!strcmp("", dut)) {
            /* Empty string passed in, treat as NULL */
            dut = NULL;
        } else {
            // Skip any library component of the toplevel
            char *dot = strchr(dut, '.');
            if (dot != NULL) {
                dut += (dot - dut + 1);
            }
        }
    }

    PyObject *cocotb_module, *cocotb_init, *cocotb_retval;
    PyObject *cocotb_log_module = NULL;
    PyObject *simlog_func;
    PyObject *argv_list;

    cocotb_module = NULL;

    // Ensure that the current thread is ready to call the Python C API
    PyGILState_STATE gstate = PyGILState_Ensure();
    to_python();

    if (get_module_ref("cocotb", &cocotb_module))
        goto cleanup;

    if (get_module_ref("cocotb.log", &cocotb_log_module)) {
        goto cleanup;
    }

    // Obtain the function to use when logging from C code
    simlog_func = PyObject_GetAttrString(cocotb_log_module, "_log_from_c");      // New reference
    if (simlog_func == NULL) {
        PyErr_Print();
        LOG_ERROR("Failed to get the _log_from_c function");
        goto cleanup;
    }
    if (!PyCallable_Check(simlog_func)) {
        LOG_ERROR("_log_from_c is not callable");
        Py_DECREF(simlog_func);
        goto cleanup;
    }

    set_log_handler(simlog_func);                                       // Note: This function steals a reference to simlog_func.

    // Obtain the function to check whether to call log function
    simlog_func = PyObject_GetAttrString(cocotb_log_module, "_filter_from_c");   // New reference
    if (simlog_func == NULL) {
        PyErr_Print();
        LOG_ERROR("Failed to get the _filter_from_c method");
        goto cleanup;
    }
    if (!PyCallable_Check(simlog_func)) {
        LOG_ERROR("_filter_from_c is not callable");
        Py_DECREF(simlog_func);
        goto cleanup;
    }

    set_log_filter(simlog_func);                                        // Note: This function steals a reference to simlog_func.

    // Build argv for cocotb module
    argv_list = PyList_New(info->argc);                                 // New reference
    if (argv_list == NULL) {
        PyErr_Print();
        LOG_ERROR("Unable to create argv list");
        goto cleanup;
    }
    for (i = 0; i < info->argc; i++) {
        PyObject *argv_item = PyString_FromString(info->argv[i]);       // New reference
        if (argv_item == NULL) {
            PyErr_Print();
            LOG_ERROR("Unable to create Python string from argv[%d] = \"%s\"", i, info->argv[i]);
            Py_DECREF(argv_list);
            goto cleanup;
        }
        PyList_SET_ITEM(argv_list, i, argv_item);                       // Note: This function steals the reference to argv_item
    }

    // Add argv list to cocotb module
    if (-1 == PyModule_AddObject(cocotb_module, "argv", argv_list)) {   // Note: This function steals the reference to argv_list if successful
        PyErr_Print();
        LOG_ERROR("Unable to set argv");
        Py_DECREF(argv_list);
        goto cleanup;
    }

    // Add argc to cocotb module
    if (-1 == PyModule_AddIntConstant(cocotb_module, "argc", info->argc)) {
        PyErr_Print();
        LOG_ERROR("Unable to set argc");
        goto cleanup;
    }

    LOG_INFO("Running on %s version %s", info->product, info->version);
    LOG_INFO("Python interpreter initialized and cocotb loaded!");

    // Now that logging has been set up ok, we initialize the testbench
    if (-1 == PyModule_AddStringConstant(cocotb_module, "SIM_NAME", info->product)) {
        PyErr_Print();
        LOG_ERROR("Unable to set SIM_NAME");
        goto cleanup;
    }

    if (-1 == PyModule_AddStringConstant(cocotb_module, "SIM_VERSION", info->version)) {
        PyErr_Print();
        LOG_ERROR("Unable to set SIM_VERSION");
        goto cleanup;
    }

    // Set language in use as an attribute to cocotb module, or None if not provided
    const char *lang = getenv("TOPLEVEL_LANG");
    PyObject *PyLang;
    if (lang) {
        PyLang = PyString_FromString(lang);                             // New reference
    } else {
        Py_INCREF(Py_None);
        PyLang = Py_None;
    }
    if (PyLang == NULL) {
        PyErr_Print();
        LOG_ERROR("Unable to create Python object for cocotb.LANGUAGE");
        goto cleanup;
    }
    if (-1 == PyObject_SetAttrString(cocotb_module, "LANGUAGE", PyLang)) {
        PyErr_Print();
        LOG_ERROR("Unable to set LANGUAGE");
        Py_DECREF(PyLang);
        goto cleanup;
    }
    Py_DECREF(PyLang);

    pEventFn = PyObject_GetAttrString(cocotb_module, "_sim_event");     // New reference
    if (pEventFn == NULL) {
        PyErr_Print();
        LOG_ERROR("Failed to get the _sim_event method");
        goto cleanup;
    }
    if (!PyCallable_Check(pEventFn)) {
        LOG_ERROR("cocotb._sim_event is not callable");
        Py_DECREF(pEventFn);
        pEventFn = NULL;
        goto cleanup;
    }

    cocotb_init = PyObject_GetAttrString(cocotb_module, "_initialise_testbench");   // New reference
    if (cocotb_init == NULL) {
        PyErr_Print();
        LOG_ERROR("Failed to get the _initialise_testbench method");
        goto cleanup;
    }
    if (!PyCallable_Check(cocotb_init)) {
        LOG_ERROR("cocotb._initialise_testbench is not callable");
        Py_DECREF(cocotb_init);
        goto cleanup;
    }

    PyObject *dut_arg;
    if (dut == NULL) {
        Py_INCREF(Py_None);
        dut_arg = Py_None;
    } else {
        dut_arg = PyString_FromString(dut);                             // New reference
    }
    if (dut_arg == NULL) {
        PyErr_Print();
        LOG_ERROR("Unable to create Python object for dut argument of _initialise_testbench");
        goto cleanup;
    }

    cocotb_retval = PyObject_CallFunctionObjArgs(cocotb_init, dut_arg, NULL);
    Py_DECREF(dut_arg);
    Py_DECREF(cocotb_init);

    if (cocotb_retval != NULL) {
        LOG_DEBUG("_initialise_testbench successful");
        Py_DECREF(cocotb_retval);
    } else {
        PyErr_Print();
        LOG_ERROR("cocotb initialization failed - exiting");
        goto cleanup;
    }

    FEXIT
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

void embed_sim_event(gpi_event_t level, const char *msg)
{
    FENTER
    /* Indicate to the upper layer a sim event occurred */

    if (pEventFn) {
        PyGILState_STATE gstate;
        to_python();
        gstate = PyGILState_Ensure();

        if (msg == NULL) {
            msg = "No message provided";
        }

#if PY_MAJOR_VERSION >= 3
        PyObject* pValue = PyObject_CallFunction(pEventFn, "ls", level, msg);
#else
        // Workaround for bpo-9369, fixed in 3.4
        static char format[] = "ls";
        PyObject* pValue = PyObject_CallFunction(pEventFn, format, level, msg);
#endif
        if (pValue == NULL) {
            PyErr_Print();
            LOG_ERROR("Passing event to upper layer failed");
        }
        Py_XDECREF(pValue);
        PyGILState_Release(gstate);
        to_simulator();
    }

    FEXIT
}
