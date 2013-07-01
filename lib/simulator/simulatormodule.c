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

/**
* @file   simulatormodule.c
* @brief Python extension to provide access to the simulator
*
* Uses GPI calls to interface to the simulator.
*/

#include "simulatormodule.h"

/**
 * @name    Callback Handling
 * @brief   Handle a callback coming from GPI
 * @ingroup python_c_api
 *
 * GILState before calling: Unknown
 *
 * GILState after calling: Unknown
 *
 * Makes one call to PyGILState_Ensure and one call to PyGILState_Release
 *
 * Returns 0 on success or 1 on a failure.
 *
 * Handles a callback from the simulator, all of which call this function.
 *
 * We extract the associated context and find the Python function (usually
 * cocotb.scheduler.react) calling it with a reference to the trigger that
 * fired. The scheduler can then call next() on all the coroutines that
 * are waiting on that particular trigger.
 *
 * TODO:
 *  - Tidy up return values
 *  - Ensure cleanup correctly in exception cases
 *
 */
int handle_gpi_callback(void *user_data)
{
    p_callback_data callback_data_p = (p_callback_data)user_data;

    if (callback_data_p->id_value != COCOTB_ACTIVE_ID) {
        fprintf(stderr, "Userdata corrupted!\n");
        return 1;
    }
    callback_data_p->id_value = COCOTB_INACTIVE_ID;


    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();

    // Python allowed

    if (!PyCallable_Check(callback_data_p->function)) {
        fprintf(stderr, "Callback fired but function isn't callable?!\n");
        PyGILState_Release(gstate);
        return 1;
    }

    // Call the callback
    PyObject *pValue = PyObject_Call(callback_data_p->function, callback_data_p->args, callback_data_p->kwargs);

    // If the return value is NULL a Python exception has occurred
    if (pValue == NULL)
    {
        fprintf(stderr, "ERROR: called callback function returned NULL\n");
        PyErr_Print();
        fprintf(stderr, "Failed to execute callback\n");
        PyGILState_Release(gstate);
        gpi_sim_end();
        return 1;
    }

    // Free up our mess
    Py_DECREF(pValue);
    Py_DECREF(callback_data_p->function);
    Py_DECREF(callback_data_p->args);

    // Free the callback data
    free(callback_data_p);

    PyGILState_Release(gstate);

    return 0;
}


static PyObject *log_msg(PyObject *self, PyObject *args)
{
    const char *name;
    const char *path;
    const char *msg;
    const char *funcname;
    int lineno;

    if (!PyArg_ParseTuple(args, "sssis", &name, &path, &funcname, &lineno, &msg))
        return NULL;

    gpi_log(name, GPIInfo, path, funcname, lineno, msg);

    return Py_BuildValue("s", "OK!");
}


// Register a callback for read only state of sim
// First argument is the function to call
// Remaining arguments are keyword arguments to be passed to the callback
static PyObject *register_readonly_callback(PyObject *self, PyObject *args)
{
    FENTER

    PyObject *fArgs;
    PyObject *function;
    char *result;

    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();

    p_callback_data callback_data_p;

    Py_ssize_t numargs = PyTuple_Size(args);

    if (numargs < 1) {
        fprintf(stderr, "Attempt to register ReadOnly callback with!\n");
        return NULL;
    }

    // Extract the callback function
    function = PyTuple_GetItem(args, 0);
    if (!PyCallable_Check(function)) {
        fprintf(stderr, "Attempt to register ReadOnly without supplying a callback!\n");
        return NULL;
    }
    Py_INCREF(function);

    // Remaining args for function
    if (numargs > 1)
        fArgs = PyTuple_GetSlice(args, 1, numargs);   // New reference
    else
        fArgs = PyTuple_New(0); // args must not be NULL, use an empty tuple if no arguments are needed.

    callback_data_p = (p_callback_data)malloc(sizeof(s_callback_data));
    if (callback_data_p == NULL) {
        printf("Failed to allocate user data\n");
    }

    // Set up the user data (no more python API calls after this!
    callback_data_p->_saved_thread_state = PyThreadState_Get();
    callback_data_p->id_value = COCOTB_ACTIVE_ID;
    callback_data_p->function = function;
    callback_data_p->args = fArgs;
    callback_data_p->kwargs = NULL;
    callback_data_p->cb_hdl = gpi_register_readonly_callback(handle_gpi_callback, (void *)callback_data_p);

    PyObject *rv = Py_BuildValue("l", callback_data_p->cb_hdl);
    PyGILState_Release(gstate);
    FEXIT

    return rv;
}


static PyObject *register_rwsynch_callback(PyObject *self, PyObject *args)
{
    FENTER

    PyObject *fArgs;
    PyObject *function;
    char *result;

    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();

    p_callback_data callback_data_p;

    Py_ssize_t numargs = PyTuple_Size(args);

    if (numargs < 1) {
        fprintf(stderr, "Attempt to register ReadOnly callback with!\n");
        return NULL;
    }

    // Extract the callback function
    function = PyTuple_GetItem(args, 0);
    if (!PyCallable_Check(function)) {
        fprintf(stderr, "Attempt to register ReadOnly without supplying a callback!\n");
        return NULL;
    }
    Py_INCREF(function);

    // Remaining args for function
    if (numargs > 1)
        fArgs = PyTuple_GetSlice(args, 1, numargs);   // New reference
    else
        fArgs = PyTuple_New(0); // args must not be NULL, use an empty tuple if no arguments are needed.

    callback_data_p = (p_callback_data)malloc(sizeof(s_callback_data));
    if (callback_data_p == NULL) {
        printf("Failed to allocate user data\n");
    }

    // Set up the user data (no more python API calls after this!
    callback_data_p->_saved_thread_state = PyThreadState_Get();
    callback_data_p->id_value = COCOTB_ACTIVE_ID;
    callback_data_p->function = function;
    callback_data_p->args = fArgs;
    callback_data_p->kwargs = NULL;
    callback_data_p->cb_hdl = gpi_register_readwrite_callback(handle_gpi_callback, (void *)callback_data_p);

    PyObject *rv = Py_BuildValue("l", callback_data_p->cb_hdl);
    PyGILState_Release(gstate);
    FEXIT

    return rv;
}


static PyObject *register_nextstep_callback(PyObject *self, PyObject *args)
{
    FENTER

    PyObject *fArgs;
    PyObject *function;
    uint64_t time_ps;
    char *result;
    PyObject *retstr;

    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();

    p_callback_data callback_data_p;

    Py_ssize_t numargs = PyTuple_Size(args);

    if (numargs < 1) {
        fprintf(stderr, "Attempt to register ReadOnly callback with!\n");
        return NULL;
    }

    // Extract the callback function
    function = PyTuple_GetItem(args, 0);
    if (!PyCallable_Check(function)) {
        fprintf(stderr, "Attempt to register ReadOnly without supplying a callback!\n");
        return NULL;
    }
    Py_INCREF(function);

    // Remaining args for function
    if (numargs > 1)
        fArgs = PyTuple_GetSlice(args, 1, numargs);   // New reference
    else
        fArgs = PyTuple_New(0); // args must not be NULL, use an empty tuple if no arguments are needed.

    callback_data_p = (p_callback_data)malloc(sizeof(s_callback_data));
    if (callback_data_p == NULL) {
        printf("Failed to allocate user data\n");
    }

    // Set up the user data (no more python API calls after this!
    callback_data_p->_saved_thread_state = PyThreadState_Get();
    callback_data_p->id_value = COCOTB_ACTIVE_ID;
    callback_data_p->function = function;
    callback_data_p->args = fArgs;
    callback_data_p->kwargs = NULL;
    callback_data_p->cb_hdl = gpi_register_nexttime_callback(handle_gpi_callback, (void *)callback_data_p);

    PyObject *rv = Py_BuildValue("l", callback_data_p->cb_hdl);
    PyGILState_Release(gstate);
    FEXIT

    return rv;
}


// Register a timed callback.
// First argument should be the time in picoseconds
// Second argument is the function to call
// Remaining arguments and keyword arguments are to be passed to the callback
static PyObject *register_timed_callback(PyObject *self, PyObject *args)
{
    FENTER

    PyObject *fArgs;
    PyObject *function;
    uint64_t time_ps;

    p_callback_data callback_data_p;

    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();

    Py_ssize_t numargs = PyTuple_Size(args);

    if (numargs < 2) {
        fprintf(stderr, "Attempt to register timed callback without enough arguments!\n");
        return NULL;
    }

    // Extract the time
    PyObject *pTime = PyTuple_GetItem(args, 0);
    time_ps = PyLong_AsLongLong(pTime);

    // Extract the callback function
    function = PyTuple_GetItem(args, 1);
    if (!PyCallable_Check(function)) {
        fprintf(stderr, "Attempt to register timed callback without passing a callable callback!\n");
        return NULL;
    }
    Py_INCREF(function);

    // Remaining args for function
    if (numargs > 2)
        fArgs = PyTuple_GetSlice(args, 2, numargs);   // New reference
    else
        fArgs = PyTuple_New(0); // args must not be NULL, use an empty tuple if no arguments are needed.


    callback_data_p = (p_callback_data)malloc(sizeof(s_callback_data));
    if (callback_data_p == NULL) {
        printf("Failed to allocate user data\n");
    }

    // Set up the user data (no more python API calls after this!
    callback_data_p->_saved_thread_state = PyThreadState_Get();
    callback_data_p->id_value = COCOTB_ACTIVE_ID;
    callback_data_p->function = function;
    callback_data_p->args = fArgs;
    callback_data_p->kwargs = NULL;
    callback_data_p->cb_hdl = gpi_register_timed_callback(handle_gpi_callback, (void *)callback_data_p, time_ps);

    // Check success
    PyObject *rv = Py_BuildValue("l", callback_data_p->cb_hdl);
    PyGILState_Release(gstate);
    FEXIT

    return rv;
}


// Register signal change callback
// First argument should be the signal handle
// Second argument is the function to call
// Remaining arguments and keyword arguments are to be passed to the callback
static PyObject *register_value_change_callback(PyObject *self, PyObject *args) //, PyObject *keywds)
{
    FENTER

    PyObject *fArgs;
    PyObject *function;
    uint64_t time_ps;
    gpi_sim_hdl sig_hdl;
    char *result;
    PyObject *retstr;



    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();

    p_callback_data callback_data_p;

    Py_ssize_t numargs = PyTuple_Size(args);

    if (numargs < 2) {
        fprintf(stderr, "Attempt to register timed callback without enough arguments!\n");
        return NULL;
    }

    PyObject *pSihHdl = PyTuple_GetItem(args, 0);
    sig_hdl = (gpi_sim_hdl)PyLong_AsUnsignedLong(pSihHdl);

    // Extract the callback function
    function = PyTuple_GetItem(args, 1);
    if (!PyCallable_Check(function)) {
        fprintf(stderr, "Attempt to register value change callback without passing a callable callback!\n");
        return NULL;
    }
    Py_INCREF(function);

    // Remaining args for function
    if (numargs > 2)
        fArgs = PyTuple_GetSlice(args, 2, numargs);   // New reference
    else
        fArgs = PyTuple_New(0); // args must not be NULL, use an empty tuple if no arguments are needed.


    callback_data_p = (p_callback_data)malloc(sizeof(s_callback_data));
    if (callback_data_p == NULL) {
        printf("Failed to allocate user data\n");
    }
    // Set up the user data (no more python API calls after this!
    // Causes segfault?
    callback_data_p->_saved_thread_state = PyThreadState_Get();//PyThreadState_Get();
    callback_data_p->id_value = COCOTB_ACTIVE_ID;
    callback_data_p->function = function;
    callback_data_p->args = fArgs;
    callback_data_p->kwargs = NULL;
    callback_data_p->cb_hdl = gpi_register_value_change_callback(handle_gpi_callback, (void *)callback_data_p, sig_hdl);

    // Check success
    PyObject *rv = Py_BuildValue("l", callback_data_p->cb_hdl);

    PyGILState_Release(gstate);
    FEXIT

    return rv;
}


static PyObject *iterate_signals(PyObject *self, PyObject *args)
{
    gpi_sim_hdl hdl;
    gpi_iterator_hdl result;

    if (!PyArg_ParseTuple(args, "l", &hdl))
        return NULL;

    result = gpi_iterate(hdl);

    return Py_BuildValue("l", result);
}


static PyObject *next(PyObject *self, PyObject *args)
{
    gpi_iterator_hdl hdl;
    gpi_sim_hdl result;

    if (!PyArg_ParseTuple(args, "l", &hdl))
        return NULL;

    result = gpi_next(hdl);

    // Raise stopiteration when we're done
    if (!result) {
        PyErr_SetNone(PyExc_StopIteration);
        return NULL;
    }

    return Py_BuildValue("l", result);
}


static PyObject *get_signal_val(PyObject *self, PyObject *args)
{
    gpi_sim_hdl hdl;
    char *result;
    PyObject *retstr;

    if (!PyArg_ParseTuple(args, "l", &hdl))
        return NULL;

    result = gpi_get_signal_value_binstr((gpi_sim_hdl)hdl);
    retstr = Py_BuildValue("s", result);
    free(result);

    return retstr;
}


static PyObject *set_signal_val(PyObject *self, PyObject *args)
{
    gpi_sim_hdl hdl;
    long value;

    if (!PyArg_ParseTuple(args, "ll", &hdl, &value))
        return NULL;

    gpi_set_signal_value_int(hdl,value);
    return Py_BuildValue("s", "OK!");
}


static PyObject *set_signal_val_str(PyObject *self, PyObject *args)
{
    gpi_sim_hdl hdl;
    const char *binstr;

    if (!PyArg_ParseTuple(args, "ls", &hdl, &binstr))
        return NULL;

    gpi_set_signal_value_str(hdl,binstr);
    return Py_BuildValue("s", "OK!");
}


static PyObject *get_handle_by_name(PyObject *self, PyObject *args)
{
    const char *name;
    gpi_sim_hdl hdl;
    gpi_sim_hdl result;

    if (!PyArg_ParseTuple(args, "ls", &hdl, &name))
        return NULL;

    result = gpi_get_handle_by_name(name, (gpi_sim_hdl)hdl);

    return Py_BuildValue("l", result);
}


static PyObject *get_name_string(PyObject *self, PyObject *args)
{
    char *result;
    gpi_sim_hdl hdl;
    PyObject *retstr;

    if (!PyArg_ParseTuple(args, "l", &hdl))
        return NULL;

    result = gpi_get_signal_name_str((gpi_sim_hdl)hdl);
    retstr = Py_BuildValue("s", result);
    free(result);

    return retstr;
}


static PyObject *get_type_string(PyObject *self, PyObject *args)
{
    char *result;
    gpi_sim_hdl hdl;
    PyObject *retstr;

    if (!PyArg_ParseTuple(args, "l", &hdl))
        return NULL;

    result = gpi_get_signal_type_str((gpi_sim_hdl)hdl);
    retstr = Py_BuildValue("s", result);
    free(result);

    return retstr;
}


// Returns a high, low tuple of simulator time
// Note we can never log from this function since the logging mechanism calls this to annotate
// log messages with the current simulation time
static PyObject *get_sim_time(PyObject *self, PyObject *args)
{

    uint32_t high, low;

    gpi_get_sim_time(&high, &low);

    PyObject *pTuple = PyTuple_New(2);
    PyTuple_SetItem(pTuple, 0, PyLong_FromUnsignedLong(high));       // Note: This function “steals” a reference to o.
    PyTuple_SetItem(pTuple, 1, PyLong_FromUnsignedLong(low));       // Note: This function “steals” a reference to o.

    return pTuple;
}


static PyObject *stop_simulator(PyObject *self, PyObject *args)
{
    gpi_sim_end();
    return Py_BuildValue("s", "OK!");    
}


static PyObject *deregister_callback(PyObject *self, PyObject *args)
{
    gpi_sim_hdl hdl;
    PyObject *pSihHdl;
    int ret;

    FENTER

    pSihHdl = PyTuple_GetItem(args, 0);
    hdl = (gpi_sim_hdl)PyLong_AsUnsignedLong(pSihHdl);

    if (!gpi_deregister_callback(hdl))
        return NULL;

    FEXIT
    return Py_BuildValue("s", "OK!");
}


static PyObject *create_clock(PyObject *self, PyObject *args)
{
    gpi_sim_hdl hdl;
    int period;
    unsigned int mcycles;

    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();

    Py_ssize_t numargs = PyTuple_Size(args);

    if (numargs < 3) {
        fprintf(stderr, "Attempt to create a clock with without enough arguments!\n");
        return NULL;
    }

    PyObject *pSihHdl = PyTuple_GetItem(args, 0);
    hdl = (gpi_sim_hdl)PyLong_AsUnsignedLong(pSihHdl);

    PyObject *pPeriod = PyTuple_GetItem(args, 1);
    period = (int)PyInt_AsLong(pPeriod);

    PyObject *pCycles = PyTuple_GetItem(args, 2);
    mcycles = (unsigned int)PyLong_AsUnsignedLong(pCycles);

    gpi_sim_hdl clk_hdl = gpi_clock_register(hdl, period, mcycles);
    PyObject *rv = Py_BuildValue("l", clk_hdl);

    PyGILState_Release(gstate);
    return rv;
}


static PyObject *stop_clock(PyObject *self, PyObject *args)
{
    gpi_sim_hdl clk_hdl;

    if (!PyArg_ParseTuple(args, "l", &clk_hdl))
       return NULL;

    gpi_clock_unregister(clk_hdl);
    PyObject *rv = Py_BuildValue("l", NULL);
    return rv;
}


PyMODINIT_FUNC
initsimulator(void)
{
    (void) Py_InitModule("simulator", SimulatorMethods);
}
