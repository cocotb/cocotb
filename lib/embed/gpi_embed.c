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

#if defined(_WIN32)
#include <windows.h>
#define sleep(n) Sleep(1000 * n)
#endif
static PyThreadState *gtstate = NULL;

#if PY_MAJOR_VERSION >= 3
static wchar_t progname[] = L"cocotb";
static wchar_t *argv[] = { progname };
#else
static char progname[] = "cocotb";
static char *argv[] = { progname };
#endif

static PyObject *pEventFn = NULL;

// Tracks if we are in the context of Python or Simulator
int context = 0;

/**
 * @name    Initialise the python interpreter
 * @brief   Create and initialise the python interpreter
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

    // Don't initialise python if already running
    if (gtstate)
        return;

    void * ret = utils_dyn_open(PY_SO_LIB);
    if (!ret) {
        fprintf(stderr, "Failed to find python lib\n");
    }

    to_python();
    Py_SetProgramName(progname);
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
            fprintf(stderr, "COCOTB_ATTACH only needs to be set to ~30 seconds");
            goto out;
        }
        if ((errno != 0 && sleep_time == 0) ||
            (sleep_time <= 0)) {
            fprintf(stderr, "COCOTB_ATTACH must be set to an integer base 10 or omitted");
            goto out;
        }

        fprintf(stderr, "Waiting for %lu seconds - Attach to %d\n", sleep_time, getpid());
        sleep(sleep_time);
    }
out:
    FEXIT;
}



/**
 * @name    Initialisation
 * @brief   Called by the simulator on initialisation. Load cocotb python module
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

#define COCOTB_MODULE "cocotb"

int get_module_ref(const char *modname, PyObject **mod)
{
    PyObject *pModule = PyImport_ImportModule(modname);

    if (pModule == NULL) {
        PyErr_Print();
        fprintf(stderr, "Failed to load \"%s\"\n", modname);
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

    /* Check that we are not already initialised */
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




    PyObject *cocotb_module, *cocotb_init, *cocotb_args, *cocotb_retval;
    PyObject *simlog_obj, *simlog_func;
    PyObject *argv_list, *argc, *arg_dict, *arg_value;

    cocotb_module = NULL;
    arg_dict = NULL;

    //Ensure that the current thread is ready to callthe Python C API
    PyGILState_STATE gstate = PyGILState_Ensure();
    to_python();

    if (get_module_ref(COCOTB_MODULE, &cocotb_module))
        goto cleanup;

    // Obtain the loggpi logger object
    simlog_obj = PyObject_GetAttrString(cocotb_module, "loggpi");

    if (simlog_obj == NULL) {
        PyErr_Print();
        fprintf(stderr, "Failed to to get simlog object\n");
    }

    simlog_func = PyObject_GetAttrString(simlog_obj, "_printRecord");
    if (simlog_func == NULL) {
        PyErr_Print();
        fprintf(stderr, "Failed to get the _printRecord method");
        goto cleanup;
    }

    if (!PyCallable_Check(simlog_func)) {
        PyErr_Print();
        fprintf(stderr, "_printRecord is not callable");
        goto cleanup;
    }

    set_log_handler(simlog_func);

    Py_DECREF(simlog_func);

    simlog_func = PyObject_GetAttrString(simlog_obj, "_willLog");
    if (simlog_func == NULL) {
        PyErr_Print();
        fprintf(stderr, "Failed to get the _willLog method");
        goto cleanup;
    }

    if (!PyCallable_Check(simlog_func)) {
        PyErr_Print();
        fprintf(stderr, "_willLog is not callable");
        goto cleanup;
    }

    set_log_filter(simlog_func);

    argv_list = PyList_New(0);
    for (i = 0; i < info->argc; i++) {
        arg_value = PyString_FromString(info->argv[i]);
        PyList_Append(argv_list, arg_value);
    }

    arg_dict = PyModule_GetDict(cocotb_module);
    PyDict_SetItemString(arg_dict, "argv", argv_list);

    argc = PyInt_FromLong(info->argc);
    PyDict_SetItemString(arg_dict, "argc", argc);

    if (!PyCallable_Check(simlog_func)) {
        PyErr_Print();
        fprintf(stderr, "_printRecord is not callable");
        goto cleanup;
    }

    LOG_INFO("Running on %s version %s", info->product, info->version);
    LOG_INFO("Python interpreter initialised and cocotb loaded!");

    // Now that logging has been set up ok we initialise the testbench
    if (-1 == PyObject_SetAttrString(cocotb_module, "SIM_NAME", PyString_FromString(info->product))) {
        PyErr_Print();
        fprintf(stderr, "Unable to set SIM_NAME");
        goto cleanup;
    }

    // Set language in use as an attribute to cocotb module, or None if not provided
    const char *lang = getenv("TOPLEVEL_LANG");
    PyObject* PyLang;
    if (lang)
        PyLang = PyString_FromString(lang);
    else
        PyLang = Py_None;

    if (-1 == PyObject_SetAttrString(cocotb_module, "LANGUAGE", PyLang)) {
        fprintf(stderr, "Unable to set LANGUAGE");
        goto cleanup;
    }

    // Hold onto a reference to our _fail_test function
    pEventFn = PyObject_GetAttrString(cocotb_module, "_sim_event");

    if (!PyCallable_Check(pEventFn)) {
        PyErr_Print();
        fprintf(stderr, "cocotb._sim_event is not callable");
        goto cleanup;
    }
    Py_INCREF(pEventFn);

    cocotb_init = PyObject_GetAttrString(cocotb_module, "_initialise_testbench");         // New reference

    if (cocotb_init == NULL || !PyCallable_Check(cocotb_init)) {
        if (PyErr_Occurred())
            PyErr_Print();
        fprintf(stderr, "Cannot find function \"%s\"\n", "_initialise_testbench");
        goto cleanup;
    }

    cocotb_args = PyTuple_New(1);
    if (dut == NULL)
        PyTuple_SetItem(cocotb_args, 0, Py_BuildValue(""));        // Note: This function “steals” a reference to o.
    else
        PyTuple_SetItem(cocotb_args, 0, PyString_FromString(dut));        // Note: This function “steals” a reference to o.
    cocotb_retval = PyObject_CallObject(cocotb_init, cocotb_args);

    if (cocotb_retval != NULL) {
        LOG_DEBUG("_initialise_testbench successful");
        Py_DECREF(cocotb_retval);
    } else {
        PyErr_Print();
        fprintf(stderr,"Cocotb initialisation failed - exiting\n");
        goto cleanup;
    }

    FEXIT
    goto ok;

cleanup:
    ret = -1;
ok:
    if (cocotb_module) {
        Py_DECREF(cocotb_module);
    }
    if (arg_dict) {
        Py_DECREF(arg_dict);
    }
    PyGILState_Release(gstate);
    to_simulator();

    return ret;
}

void embed_sim_event(gpi_event_t level, const char *msg)
{
    FENTER
    /* Indicate to the upper layer a sim event occoured */

    if (pEventFn) {
        PyGILState_STATE gstate;
        to_python();
        gstate = PyGILState_Ensure();

        PyObject *fArgs = PyTuple_New(2);
        PyTuple_SetItem(fArgs, 0, PyInt_FromLong(level));

        if (msg != NULL)
            PyTuple_SetItem(fArgs, 1, PyString_FromString(msg));
        else
            PyTuple_SetItem(fArgs, 1, PyString_FromString("No message provided"));
        PyObject *pValue = PyObject_CallObject(pEventFn, fArgs);
        if (!pValue) {
            LOG_ERROR("Passing event to upper layer failed");
        }

        Py_DECREF(fArgs);
        PyGILState_Release(gstate);
        to_simulator();
    }

    FEXIT
}
