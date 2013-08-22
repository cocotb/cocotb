/******************************************************************************
* Copyright (c) 2013 Potential Ventures Ltd
* All rights reserved.
*
* Redistribution and use in source and binary forms, with or without
* modification, are permitted provided that the following conditions are met:
*    * Redistributions of source code must retain the above copyright
*      notice, this list of conditions and the following disclaimer.
*    * Redistributions in binary form must reproduce the above copyright
*      notice, this list of conditions and the following disclaimer in the
*      documentation and/or other materials provided with the distribution.
*    * Neither the name of Potential Ventures Ltd nor the
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
#include "embed.h"

static PyThreadState *gtstate;

static char progname[] = "cocotb";
static PyObject *thread_dict;
static PyObject *pEventFn;


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

    // Don't initialise python if already running
    if (gtstate)
        return;

    Py_SetProgramName(progname);
    Py_Initialize();                    /* Initialize the interpreter */
    PyEval_InitThreads();               /* Create (and acquire) the interpreter lock */

    /* Swap out and return current thread state and release the GIL */
    gtstate = PyEval_SaveThread();
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
    PyObject *pModule = PyImport_Import(PyString_FromString(modname));

    if (pModule == NULL) {
        PyErr_Print();
        fprintf(stderr, "Failed to load \"%s\"\n", modname);
        return -1;
    }

    *mod = pModule;
    return 0;
}

void embed_sim_init(gpi_sim_info_t *info)
{
    FENTER

    int i;

    // Find the simulation root
    gpi_sim_hdl dut = gpi_get_root_handle(getenv("TOPLEVEL"));

    if (dut == NULL) {
        fprintf(stderr, "Unable to find root instance!\n");
        gpi_sim_end();
        return;
    }

    PyObject *cocotb_module, *cocotb_init, *cocotb_args, *cocotb_retval;
    PyObject *simlog_class, *simlog_obj, *simlog_args, *simlog_func;
    PyObject *argv_list, *argc, *arg_dict, *arg_value;


    //Ensure that the current thread is ready to callthe Python C API
    PyGILState_STATE gstate = PyGILState_Ensure();

    if (get_module_ref(COCOTB_MODULE, &cocotb_module))
        goto cleanup;

    // Create a logger object
    simlog_obj = PyObject_GetAttrString(cocotb_module, "log");

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

    LOG_INFO("Python interpreter initialised and cocotb loaded!");

    // Now that logging has been set up ok we initialise the testbench

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
        Py_DECREF(cocotb_init);
        goto cleanup;
    }

    cocotb_args = PyTuple_New(1);
    PyTuple_SetItem(cocotb_args, 0, PyLong_FromLong((long)dut));        // Note: This function “steals” a reference to o.
    cocotb_retval = PyObject_CallObject(cocotb_init, cocotb_args);

    if (cocotb_retval != NULL) {
        LOG_INFO("_initialise_testbench successful");
        Py_DECREF(cocotb_retval);
    } else {
        PyErr_Print();
        fprintf(stderr,"Call failed\n");
        gpi_sim_end();
        goto cleanup;
    }

    FEXIT

cleanup:
    if (cocotb_module)
        Py_DECREF(cocotb_module);
    if (arg_dict)
        Py_DECREF(arg_dict);
    PyGILState_Release(gstate);
}

void embed_sim_event(gpi_event_t level, const char *msg)
{
    FENTER
    /* Indicate to the upper layer a sim event occoured */

    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();

    LOG_WARN("Failing the test at simulator request!");

    PyObject *fArgs = PyTuple_New(2);
    PyTuple_SetItem(fArgs, 0, PyInt_FromLong(level));
    PyTuple_SetItem(fArgs, 1, PyString_FromString(msg));
    PyObject *pValue = PyObject_Call(pEventFn, fArgs, NULL);

    Py_DECREF(fArgs);
    PyGILState_Release(gstate);

    FEXIT
}
