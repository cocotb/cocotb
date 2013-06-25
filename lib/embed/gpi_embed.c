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
#include "gpi.h"
#include "gpi_logging.h"

static PyThreadState *gtstate;
static gpi_cb_hdl sim_init_cb;
static gpi_cb_hdl sim_finish_cb;



static char *progname = "cocotb";
static PyObject *thread_dict;
static PyObject *lock;



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
void init_python(void)
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
int handle_sim_init(void *gpi_cb_data)
{
    FENTER

    // Find the simulation root
    gpi_sim_hdl dut = gpi_get_root_handle();

    PyObject *pName, *pModule, *pDict, *pFunc, *pArgs;
    PyObject *pValue, *pLogger;


    //Ensure that the current thread is ready to callthe Python C API
    PyGILState_STATE gstate = PyGILState_Ensure();
    // Python allowed

    pModule = PyImport_Import(PyString_FromString("cocotb"));

    if (pModule == NULL)
    {
        PyErr_Print();
        fprintf(stderr, "Failed to load \"%s\"\n", "cocotb");
        PyGILState_Release(gstate);
        return 1;
    }


    // Extact a reference to the logger object to unitfy logging mechanism
    pLogger = PyObject_GetAttrString(pModule, "log");
    PyObject *pHandler= PyObject_GetAttrString(pLogger, "handle");              // New reference
    PyObject *pRecordFn= PyObject_GetAttrString(pLogger, "makeRecord");
    PyObject *pFilterFn= PyObject_GetAttrString(pLogger, "filter");

    if (pLogger == NULL || pHandler == NULL || pRecordFn == NULL)
    {
        PyErr_Print();
        fprintf(stderr, "Failed to find handle to logging object \"log\" from module cocotb\n");
        PyGILState_Release(gstate);
        return 1;
    }

    set_log_handler(pHandler);
    set_make_record(pRecordFn);
    set_log_filter(pFilterFn);


    Py_DECREF(pLogger);
    Py_DECREF(pHandler);
    Py_DECREF(pRecordFn);
    Py_DECREF(pFilterFn);

    // Save a handle to the lock object
    lock = PyObject_GetAttrString(pModule, "_rlock");

    LOG_INFO("Python interpreter initialised and cocotb loaded!");

    pFunc = PyObject_GetAttrString(pModule, "_initialise_testbench");         // New reference

    if (pFunc == NULL || !PyCallable_Check(pFunc))
    {
        if (PyErr_Occurred())
            PyErr_Print();
        fprintf(stderr, "Cannot find function \"%s\"\n", "_initialise_testbench");
        Py_DECREF(pFunc);
        Py_DECREF(pModule);
        PyGILState_Release(gstate);
        return 1;
    }

    pArgs = PyTuple_New(1);
    PyTuple_SetItem(pArgs, 0, PyLong_FromLong((long)dut));        // Note: This function “steals” a reference to o.
    pValue = PyObject_CallObject(pFunc, pArgs);

    if (pValue != NULL)
    {
        LOG_INFO("_initialise_testbench successful");
        Py_DECREF(pValue);
    } else {
        PyErr_Print();
        fprintf(stderr,"Call failed\n");
        gpi_sim_end();
    }

    Py_DECREF(pFunc);
    Py_DECREF(pModule);

    PyGILState_Release(gstate);

    FEXIT
    return(0);
}

void register_initial_callback()
{
    FENTER
    sim_init_cb = gpi_register_sim_start_callback(handle_sim_init, (void *)NULL);
    FEXIT
}


// NB We don't attempt to log here since the world has fallen apart
int handle_sim_end(void *gpi_cb_data)
{
    return(0);
}

void register_final_callback()
{
    FENTER
    sim_finish_cb = gpi_register_sim_end_callback(handle_sim_end, (void *)NULL);
    FEXIT
}


// FIXME this is VPI specific, should be in gpi_vpi.c
void (*vlog_startup_routines[])() = {
   init_python,
   register_initial_callback,
   register_final_callback,
   0
};


// For non-VPI compliant applications that cannot find vlog_startup_routines symbol
void vlog_startup_routines_bootstrap() {
   void (*routine)(void);
   int i;
   routine = vlog_startup_routines[0];
   for (i = 0, routine = vlog_startup_routines[i];
        routine;
        routine = vlog_startup_routines[++i]) {
       routine();
   }
}
