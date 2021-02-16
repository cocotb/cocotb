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

/**
* @file   simulatormodule.c
* @brief Python extension to provide access to the simulator
*
* Uses GPI calls to interface to the simulator.
*/

static int takes = 0;
static int releases = 0;

static int sim_ending = 0;

#include <cocotb_utils.h>       // COCOTB_UNUSED
#include <type_traits>
#include <limits>
#include <Python.h>
#include <gpi_logging.h>        // LOG_* macros
#include <py_gpi_logging.h>     // py_gpi_logger_set_level
#include "gpi.h"

// This file defines the routines available to Python

#define COCOTB_ACTIVE_ID        0xC0C07B        // User data flag to indicate callback is active
#define COCOTB_INACTIVE_ID      0xDEADB175      // User data flag set when callback has been de-registered

#define MODULE_NAME "simulator"

// callback user data
struct callback_data {
    PyThreadState *_saved_thread_state; // Thread state of the calling thread FIXME is this required?
    uint32_t id_value;                  // COCOTB_ACTIVE_ID or COCOTB_INACTIVE_ID
    PyObject *function;                 // Function to call when the callback fires
    PyObject *args;                     // The arguments to call the function with
    PyObject *kwargs;                   // Keyword arguments to call the function with
    gpi_sim_hdl cb_hdl;
};

/* define the extension types as templates */
namespace {
    template<typename gpi_hdl>
    struct gpi_hdl_Object {
        PyObject_HEAD
        gpi_hdl hdl;

        // The python type object, in a place that is easy to retrieve in templates
        static PyTypeObject py_type;
    };

    /** __repr__ shows the memory address of the internal handle */
    template<typename gpi_hdl>
    static PyObject *gpi_hdl_repr(gpi_hdl_Object<gpi_hdl> *self) {
        auto *type = Py_TYPE(self);
        return PyUnicode_FromFormat("<%s at %p>", type->tp_name, self->hdl);
    }

    /** __hash__ returns the pointer itself */
    template<typename gpi_hdl>
    static Py_hash_t gpi_hdl_hash(gpi_hdl_Object<gpi_hdl> *self) {
        auto ret = reinterpret_cast<Py_hash_t>(self->hdl);
        // hash must never return -1
        if (ret == (Py_hash_t)-1) {
            ret = (Py_hash_t)-2;
        }
        return ret;
    }

    /**
     * Create a new python handle object from a pointer, returning None if the
     * pointer is NULL.
     */
    template<typename gpi_hdl>
    static PyObject *gpi_hdl_New(gpi_hdl hdl) {
        if (hdl == NULL) {
            Py_RETURN_NONE;
        }
        auto *obj = PyObject_New(gpi_hdl_Object<gpi_hdl>, &gpi_hdl_Object<gpi_hdl>::py_type);
        if (obj == NULL) {
            return NULL;
        }
        obj->hdl = hdl;
        return (PyObject *)obj;
    }

    /** Comparison checks if the types match, and then compares pointers */
    template<typename gpi_hdl>
    static PyObject *gpi_hdl_richcompare(PyObject *self, PyObject *other, int op) {
        if (
            Py_TYPE(self) != &gpi_hdl_Object<gpi_hdl>::py_type ||
            Py_TYPE(other) != &gpi_hdl_Object<gpi_hdl>::py_type
        ) {
            Py_RETURN_NOTIMPLEMENTED;
        }

        auto self_hdl_obj = reinterpret_cast<gpi_hdl_Object<gpi_hdl>*>(self);
        auto other_hdl_obj = reinterpret_cast<gpi_hdl_Object<gpi_hdl>*>(other);

        switch (op) {
            case Py_EQ: return PyBool_FromLong(self_hdl_obj->hdl == other_hdl_obj->hdl);
            case Py_NE: return PyBool_FromLong(self_hdl_obj->hdl != other_hdl_obj->hdl);
            default: Py_RETURN_NOTIMPLEMENTED;
        }
    }

    // Initialize the python type slots
    template<typename gpi_hdl>
    PyTypeObject fill_common_slots() {
        PyTypeObject type = {};
        type.ob_base = {PyObject_HEAD_INIT(NULL) 0};
        type.tp_basicsize = sizeof(gpi_hdl_Object<gpi_hdl>);
        type.tp_repr = (reprfunc)gpi_hdl_repr<gpi_hdl>;
        type.tp_hash = (hashfunc)gpi_hdl_hash<gpi_hdl>;
        type.tp_flags = Py_TPFLAGS_DEFAULT;
        type.tp_richcompare = gpi_hdl_richcompare<gpi_hdl>;
        return type;
    }

    // these will be initialized later, once the members are all defined
    template<>
    PyTypeObject gpi_hdl_Object<gpi_sim_hdl>::py_type;
    template<>
    PyTypeObject gpi_hdl_Object<gpi_iterator_hdl>::py_type;
    template<>
    PyTypeObject gpi_hdl_Object<gpi_cb_hdl>::py_type;
}


typedef int (*gpi_function_t)(const void *);

PyGILState_STATE TAKE_GIL(void)
{
    PyGILState_STATE state = PyGILState_Ensure();
    takes ++;
    return state;
}

void DROP_GIL(PyGILState_STATE state)
{
    PyGILState_Release(state);
    releases++;
}

struct sim_time {
    uint32_t high;
    uint32_t low;
};

static struct sim_time cache_time;

/**
 * @name    Callback Handling
 * @brief   Handle a callback coming from GPI
 * @ingroup python_c_api
 *
 * GILState before calling: Unknown
 *
 * GILState after calling: Unknown
 *
 * Makes one call to TAKE_GIL and one call to DROP_GIL
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
    int ret = 0;
    to_python();
    callback_data *cb_data = (callback_data *)user_data;

    if (cb_data->id_value != COCOTB_ACTIVE_ID) {
        fprintf(stderr, "Userdata corrupted!\n");
        ret = 1;
        goto err;
    }
    cb_data->id_value = COCOTB_INACTIVE_ID;

    /* Cache the sim time */
    gpi_get_sim_time(&cache_time.high, &cache_time.low);

    PyGILState_STATE gstate;
    gstate = TAKE_GIL();

    // Python allowed

    if (!PyCallable_Check(cb_data->function)) {
        fprintf(stderr, "Callback fired but function isn't callable?!\n");
        ret = 1;
        goto out;
    }

    {
        // Call the callback
        PyObject *pValue = PyObject_Call(cb_data->function, cb_data->args, cb_data->kwargs);

        // If the return value is NULL a Python exception has occurred
        // The best thing to do here is shutdown as any subsequent
        // calls will go back to Python which is now in an unknown state
        if (pValue == NULL) {
            fprintf(stderr, "ERROR: called callback function threw exception\n");
            PyErr_Print();

            gpi_sim_end();
            sim_ending = 1;
            ret = 0;
            goto out;
        }

        // Free up our mess
        Py_DECREF(pValue);
    }

    // Callbacks may have been re-enabled
    if (cb_data->id_value == COCOTB_INACTIVE_ID) {
        Py_DECREF(cb_data->function);
        Py_DECREF(cb_data->args);

        // Free the callback data
        free(cb_data);
    }

out:
    DROP_GIL(gstate);

err:
    to_simulator();

    if (sim_ending) {
        // This is the last callback of a successful run,
        // so call the cleanup function as we'll never return
        // to Python
        gpi_cleanup();
    }
    return ret;
}

static PyObject *log_msg(PyObject *self, PyObject *args)
{
    COCOTB_UNUSED(self);

    const char *name;
    const char *path;
    const char *msg;
    const char *funcname;
    int lineno;

    if (!PyArg_ParseTuple(args, "sssis:log_msg", &name, &path, &funcname, &lineno, &msg))
        return NULL;

    gpi_log(name, GPIInfo, path, funcname, lineno, msg);

    Py_RETURN_NONE;
}


static callback_data *callback_data_new(PyObject *func, PyObject *args, PyObject *kwargs)
{
    callback_data *data = (callback_data *)malloc(sizeof(callback_data));
    if (data == NULL) {
        PyErr_NoMemory();
        return NULL;
    }

    data->_saved_thread_state = PyThreadState_Get();
    data->id_value = COCOTB_ACTIVE_ID;
    data->function = func;
    data->args = args;
    data->kwargs = kwargs;

    return data;
}


// Register a callback for read-only state of sim
// First argument is the function to call
// Remaining arguments are keyword arguments to be passed to the callback
static PyObject *register_readonly_callback(PyObject *self, PyObject *args)
{
    COCOTB_UNUSED(self);

    if (!gpi_has_registered_impl()) {
        PyErr_SetString(PyExc_RuntimeError, "No simulator available!");
        return NULL;
    }

    Py_ssize_t numargs = PyTuple_Size(args);

    if (numargs < 1) {
        PyErr_SetString(PyExc_TypeError, "Attempt to register ReadOnly callback without enough arguments!\n");
        return NULL;
    }

    // Extract the callback function
    PyObject *function = PyTuple_GetItem(args, 0);
    if (!PyCallable_Check(function)) {
        PyErr_SetString(PyExc_TypeError, "Attempt to register ReadOnly without supplying a callback!\n");
        return NULL;
    }
    Py_INCREF(function);

    // Remaining args for function
    PyObject *fArgs = PyTuple_GetSlice(args, 1, numargs);   // New reference
    if (fArgs == NULL) {
        return NULL;
    }

    callback_data *cb_data = callback_data_new(function, fArgs, NULL);
    if (cb_data == NULL) {
        return NULL;
    }

    gpi_cb_hdl hdl = gpi_register_readonly_callback((gpi_function_t)handle_gpi_callback, cb_data);

    PyObject *rv = gpi_hdl_New(hdl);

    return rv;
}


static PyObject *register_rwsynch_callback(PyObject *self, PyObject *args)
{
    COCOTB_UNUSED(self);

    if (!gpi_has_registered_impl()) {
        PyErr_SetString(PyExc_RuntimeError, "No simulator available!");
        return NULL;
    }

    Py_ssize_t numargs = PyTuple_Size(args);

    if (numargs < 1) {
        PyErr_SetString(PyExc_TypeError, "Attempt to register ReadWrite callback without enough arguments!\n");
        return NULL;
    }

    // Extract the callback function
    PyObject *function = PyTuple_GetItem(args, 0);
    if (!PyCallable_Check(function)) {
        PyErr_SetString(PyExc_TypeError, "Attempt to register ReadWrite without supplying a callback!\n");
        return NULL;
    }
    Py_INCREF(function);

    // Remaining args for function
    PyObject *fArgs = PyTuple_GetSlice(args, 1, numargs);   // New reference
    if (fArgs == NULL) {
        return NULL;
    }

    callback_data *cb_data = callback_data_new(function, fArgs, NULL);
    if (cb_data == NULL) {
        return NULL;
    }

    gpi_cb_hdl hdl = gpi_register_readwrite_callback(
        (gpi_function_t)handle_gpi_callback, cb_data);

    PyObject *rv = gpi_hdl_New(hdl);

    return rv;
}


static PyObject *register_nextstep_callback(PyObject *self, PyObject *args)
{
    COCOTB_UNUSED(self);

    if (!gpi_has_registered_impl()) {
        PyErr_SetString(PyExc_RuntimeError, "No simulator available!");
        return NULL;
    }

    Py_ssize_t numargs = PyTuple_Size(args);

    if (numargs < 1) {
        PyErr_SetString(PyExc_TypeError, "Attempt to register NextStep callback without enough arguments!\n");
        return NULL;
    }

    // Extract the callback function
    PyObject *function = PyTuple_GetItem(args, 0);
    if (!PyCallable_Check(function)) {
        PyErr_SetString(PyExc_TypeError, "Attempt to register NextStep without supplying a callback!\n");
        return NULL;
    }
    Py_INCREF(function);

    // Remaining args for function
    PyObject *fArgs = PyTuple_GetSlice(args, 1, numargs);   // New reference
    if (fArgs == NULL) {
        return NULL;
    }

    callback_data *cb_data = callback_data_new(function, fArgs, NULL);
    if (cb_data == NULL) {
        return NULL;
    }

    gpi_cb_hdl hdl = gpi_register_nexttime_callback(
        (gpi_function_t)handle_gpi_callback, cb_data);

    PyObject *rv = gpi_hdl_New(hdl);

    return rv;
}


// Register a timed callback.
// First argument should be the time in picoseconds
// Second argument is the function to call
// Remaining arguments and keyword arguments are to be passed to the callback
static PyObject *register_timed_callback(PyObject *self, PyObject *args)
{
    COCOTB_UNUSED(self);

    if (!gpi_has_registered_impl()) {
        PyErr_SetString(PyExc_RuntimeError, "No simulator available!");
        return NULL;
    }

    Py_ssize_t numargs = PyTuple_Size(args);

    if (numargs < 2) {
        PyErr_SetString(PyExc_TypeError, "Attempt to register timed callback without enough arguments!\n");
        return NULL;
    }

    uint64_t time;
    {   // Extract the time
        PyObject *pTime = PyTuple_GetItem(args, 0);
        long long pTime_as_longlong = PyLong_AsLongLong(pTime);
        if (pTime_as_longlong == -1 && PyErr_Occurred()) {
            return NULL;
        } else if (pTime_as_longlong < 0) {
            PyErr_SetString(PyExc_ValueError, "Timer value must be a positive integer");
            return NULL;
        } else {
            time = (uint64_t)pTime_as_longlong;
        }
    }

    // Extract the callback function
    PyObject *function = PyTuple_GetItem(args, 1);
    if (!PyCallable_Check(function)) {
        PyErr_SetString(PyExc_TypeError, "Attempt to register timed callback without passing a callable callback!\n");
        return NULL;
    }
    Py_INCREF(function);

    // Remaining args for function
    PyObject *fArgs = PyTuple_GetSlice(args, 2, numargs);   // New reference
    if (fArgs == NULL) {
        return NULL;
    }

    callback_data *cb_data = callback_data_new(function, fArgs, NULL);
    if (cb_data == NULL) {
        return NULL;
    }

    gpi_cb_hdl hdl = gpi_register_timed_callback(
        (gpi_function_t)handle_gpi_callback, cb_data, time);

    // Check success
    PyObject *rv = gpi_hdl_New(hdl);

    return rv;
}


// Register signal change callback
// First argument should be the signal handle
// Second argument is the function to call
// Remaining arguments and keyword arguments are to be passed to the callback
static PyObject *register_value_change_callback(PyObject *self, PyObject *args) //, PyObject *keywds)
{
    COCOTB_UNUSED(self);

    if (!gpi_has_registered_impl()) {
        PyErr_SetString(PyExc_RuntimeError, "No simulator available!");
        return NULL;
    }

    Py_ssize_t numargs = PyTuple_Size(args);

    if (numargs < 3) {
        PyErr_SetString(PyExc_TypeError, "Attempt to register value change callback without enough arguments!\n");
        return NULL;
    }

    PyObject *pSigHdl = PyTuple_GetItem(args, 0);
    if (Py_TYPE(pSigHdl) != &gpi_hdl_Object<gpi_sim_hdl>::py_type) {
        PyErr_SetString(PyExc_TypeError, "First argument must be a gpi_sim_hdl");
        return NULL;
    }
    gpi_sim_hdl sig_hdl = ((gpi_hdl_Object<gpi_sim_hdl> *)pSigHdl)->hdl;

    // Extract the callback function
    PyObject *function = PyTuple_GetItem(args, 1);
    if (!PyCallable_Check(function)) {
        PyErr_SetString(PyExc_TypeError, "Attempt to register value change callback without passing a callable callback!\n");
        return NULL;
    }
    Py_INCREF(function);

    PyObject *pedge = PyTuple_GetItem(args, 2);
    int edge = (int)PyLong_AsLong(pedge);

    // Remaining args for function
    PyObject *fArgs = PyTuple_GetSlice(args, 3, numargs);   // New reference
    if (fArgs == NULL) {
        return NULL;
    }

    callback_data *cb_data = callback_data_new(function, fArgs, NULL);
    if (cb_data == NULL) {
        return NULL;
    }

    gpi_cb_hdl hdl = gpi_register_value_change_callback(
        (gpi_function_t)handle_gpi_callback, cb_data, sig_hdl, edge);

    // Check success
    PyObject *rv = gpi_hdl_New(hdl);

    return rv;
}


static PyObject *iterate(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *args)
{
    int type;

    if (!PyArg_ParseTuple(args, "i:iterate", &type)) {
        return NULL;
    }

    gpi_iterator_hdl result = gpi_iterate(self->hdl, (gpi_iterator_sel_t)type);

    return gpi_hdl_New(result);
}


static PyObject *next(gpi_hdl_Object<gpi_iterator_hdl> *self)
{
    gpi_sim_hdl result = gpi_next(self->hdl);

    // Raise StopIteration when we're done
    if (!result) {
        PyErr_SetNone(PyExc_StopIteration);
        return NULL;
    }

    return gpi_hdl_New(result);
}

// Raise an exception on failure
// Return None if for example get bin_string on enum?

static PyObject *get_signal_val_binstr(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *args)
{
    COCOTB_UNUSED(args);
    const char *result = gpi_get_signal_value_binstr(self->hdl);
    return PyUnicode_FromString(result);
}

static PyObject *get_signal_val_str(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *args)
{
    COCOTB_UNUSED(args);
    const char *result = gpi_get_signal_value_str(self->hdl);
    return PyBytes_FromString(result);
}

static PyObject *get_signal_val_real(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *args)
{
    COCOTB_UNUSED(args);
    double result = gpi_get_signal_value_real(self->hdl);
    return PyFloat_FromDouble(result);
}


static PyObject *get_signal_val_long(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *args)
{
    COCOTB_UNUSED(args);
    long result = gpi_get_signal_value_long(self->hdl);
    return PyLong_FromLong(result);
}

static PyObject *set_signal_val_binstr(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *args)
{
    const char *binstr;
    gpi_set_action_t action;

    if (!PyArg_ParseTuple(args, "is:set_signal_val_binstr", &action, &binstr)) {
        return NULL;
    }

    gpi_set_signal_value_binstr(self->hdl, binstr, action);
    Py_RETURN_NONE;
}

static PyObject *set_signal_val_str(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *args)
{
    gpi_set_action_t action;
    const char *str;

    if (!PyArg_ParseTuple(args, "iy:set_signal_val_str", &action, &str)) {
        return NULL;
    }

    gpi_set_signal_value_str(self->hdl, str, action);
    Py_RETURN_NONE;
}

static PyObject *set_signal_val_real(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *args)
{
    double value;
    gpi_set_action_t action;

    if (!PyArg_ParseTuple(args, "id:set_signal_val_real", &action, &value)) {
        return NULL;
    }

    gpi_set_signal_value_real(self->hdl, value, action);
    Py_RETURN_NONE;
}

static PyObject *set_signal_val_int(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *args)
{
    long long value;
    gpi_set_action_t action;

    if (!PyArg_ParseTuple(args, "iL:set_signal_val_int", &action, &value)) {
        return NULL;
    }

    gpi_set_signal_value_int(self->hdl, static_cast<int32_t>(value), action);
    Py_RETURN_NONE;
}

static PyObject *get_definition_name(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *args)
{
    COCOTB_UNUSED(args);
    const char* result = gpi_get_definition_name(self->hdl);
    return PyUnicode_FromString(result);
}

static PyObject *get_definition_file(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *args)
{
    COCOTB_UNUSED(args);
    const char* result = gpi_get_definition_file(self->hdl);
    return PyUnicode_FromString(result);
}

static PyObject *get_handle_by_name(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *args)
{
    const char *name;

    if (!PyArg_ParseTuple(args, "s:get_handle_by_name", &name)) {
        return NULL;
    }

    gpi_sim_hdl result = gpi_get_handle_by_name(self->hdl, name);

    return gpi_hdl_New(result);
}

static PyObject *get_handle_by_index(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *args)
{
    int32_t index;

    if (!PyArg_ParseTuple(args, "i:get_handle_by_index", &index)) {
        return NULL;
    }

    gpi_sim_hdl result = gpi_get_handle_by_index(self->hdl, index);

    return gpi_hdl_New(result);
}

static PyObject *get_root_handle(PyObject *self, PyObject *args)
{
    COCOTB_UNUSED(self);
    const char *name;

    if (!gpi_has_registered_impl()) {
        PyErr_SetString(PyExc_RuntimeError, "No simulator available!");
        return NULL;
    }

    if (!PyArg_ParseTuple(args, "z:get_root_handle", &name)) {
        return NULL;
    }

    gpi_sim_hdl result = gpi_get_root_handle(name);
    if (NULL == result) {
       Py_RETURN_NONE;
    }

    return gpi_hdl_New(result);
}


static PyObject *get_name_string(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *args)
{
    COCOTB_UNUSED(args);
    COCOTB_UNUSED(self);
    const char *result = gpi_get_signal_name_str(self->hdl);
    return PyUnicode_FromString(result);
}

static PyObject *get_type(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *args)
{
    COCOTB_UNUSED(args);
    gpi_objtype_t result = gpi_get_object_type(self->hdl);
    return PyLong_FromLong(result);
}

static PyObject *get_const(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *args)
{
    COCOTB_UNUSED(args);
    int result = gpi_is_constant(self->hdl);
    return PyBool_FromLong(result);
}

static PyObject *get_type_string(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *args)
{
    COCOTB_UNUSED(args);
    const char *result = gpi_get_signal_type_str(self->hdl);
    return PyUnicode_FromString(result);
}


static PyObject *is_running(PyObject *self, PyObject *args)
{
    COCOTB_UNUSED(self);
    COCOTB_UNUSED(args);

    return PyBool_FromLong(gpi_has_registered_impl());
}

// Returns a high, low, tuple of simulator time
// Note we can never log from this function since the logging mechanism calls this to annotate
// log messages with the current simulation time
static PyObject *get_sim_time(PyObject *self, PyObject *args)
{
    COCOTB_UNUSED(self);
    COCOTB_UNUSED(args);

    if (!gpi_has_registered_impl()) {
        PyErr_SetString(PyExc_RuntimeError, "No simulator available!");
        return NULL;
    }

    struct sim_time local_time;

    if (is_python_context) {
        gpi_get_sim_time(&local_time.high, &local_time.low);
    } else {
        local_time = cache_time;
    }

    PyObject *pTuple = PyTuple_New(2);
    PyTuple_SetItem(pTuple, 0, PyLong_FromUnsignedLong(local_time.high));       // Note: This function “steals” a reference to o.
    PyTuple_SetItem(pTuple, 1, PyLong_FromUnsignedLong(local_time.low));       // Note: This function “steals” a reference to o.

    return pTuple;
}

static PyObject *get_precision(PyObject *self, PyObject *args)
{
    COCOTB_UNUSED(self);
    COCOTB_UNUSED(args);

    if (!gpi_has_registered_impl()) {
        char const * msg = "Simulator is not available! Defaulting precision to 1 fs.";
        if (PyErr_WarnEx(PyExc_RuntimeWarning, msg, 1) < 0) {
            return NULL;
        }
        return PyLong_FromLong(-15);  // preserves old behavior
    }

    int32_t precision;

    gpi_get_sim_precision(&precision);

    return PyLong_FromLong(precision);
}

static PyObject *get_simulator_product(PyObject *m, PyObject *args)
{
    COCOTB_UNUSED(m);
    COCOTB_UNUSED(args);

    if (!gpi_has_registered_impl()) {
        PyErr_SetString(PyExc_RuntimeError, "No simulator available!");
        return NULL;
    }

    return PyUnicode_FromString(gpi_get_simulator_product());
}

static PyObject *get_simulator_version(PyObject *m, PyObject *args)
{
    COCOTB_UNUSED(m);
    COCOTB_UNUSED(args);

    if (!gpi_has_registered_impl()) {
        PyErr_SetString(PyExc_RuntimeError, "No simulator available!");
        return NULL;
    }

    return PyUnicode_FromString(gpi_get_simulator_version());
}

static PyObject *get_num_elems(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *args)
{
    COCOTB_UNUSED(args);
    int elems = gpi_get_num_elems(self->hdl);
    return PyLong_FromLong(elems);
}

static PyObject *get_range(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *args)
{
    COCOTB_UNUSED(args);

    int indexable = gpi_is_indexable(self->hdl);
    int rng_left  = gpi_get_range_left(self->hdl);
    int rng_right = gpi_get_range_right(self->hdl);

    if (indexable) {
        return Py_BuildValue("(i,i)", rng_left, rng_right);
    }
    else {
        Py_RETURN_NONE;
    }
}

static PyObject *stop_simulator(PyObject *self, PyObject *args)
{
    COCOTB_UNUSED(self);
    COCOTB_UNUSED(args);

    if (!gpi_has_registered_impl()) {
        PyErr_SetString(PyExc_RuntimeError, "No simulator available!");
        return NULL;
    }

    gpi_sim_end();
    sim_ending = 1;
    Py_RETURN_NONE;
}


static PyObject *deregister(gpi_hdl_Object<gpi_cb_hdl> *self, PyObject *args)
{
    COCOTB_UNUSED(args);

    gpi_deregister_callback(self->hdl);

    Py_RETURN_NONE;
}


static PyObject *log_level(PyObject *self, PyObject *args)
{
    COCOTB_UNUSED(self);

    int l_level;

    if (!PyArg_ParseTuple(args, "i:log_level", &l_level)) {
        return NULL;
    }

    py_gpi_logger_set_level(l_level);

    Py_RETURN_NONE;
}

static int add_module_constants(PyObject* simulator)
{
    // Make the GPI constants accessible from the C world
    if (
        PyModule_AddIntConstant(simulator, "UNKNOWN",   GPI_UNKNOWN   ) < 0 ||
        PyModule_AddIntConstant(simulator, "MEMORY",    GPI_MEMORY    ) < 0 ||
        PyModule_AddIntConstant(simulator, "MODULE",    GPI_MODULE    ) < 0 ||
        PyModule_AddIntConstant(simulator, "NET",       GPI_NET       ) < 0 ||
        // PyModule_AddIntConstant(simulator, "PARAMETER", GPI_PARAMETER ) < 0 ||  // Deprecated
        PyModule_AddIntConstant(simulator, "REG",       GPI_REGISTER  ) < 0 ||
        PyModule_AddIntConstant(simulator, "NETARRAY",  GPI_ARRAY     ) < 0 ||
        PyModule_AddIntConstant(simulator, "ENUM",      GPI_ENUM      ) < 0 ||
        PyModule_AddIntConstant(simulator, "STRUCTURE", GPI_STRUCTURE ) < 0 ||
        PyModule_AddIntConstant(simulator, "REAL",      GPI_REAL      ) < 0 ||
        PyModule_AddIntConstant(simulator, "INTEGER",   GPI_INTEGER   ) < 0 ||
        PyModule_AddIntConstant(simulator, "STRING",    GPI_STRING    ) < 0 ||
        PyModule_AddIntConstant(simulator, "GENARRAY",  GPI_GENARRAY  ) < 0 ||
        PyModule_AddIntConstant(simulator, "OBJECTS",   GPI_OBJECTS   ) < 0 ||
        PyModule_AddIntConstant(simulator, "DRIVERS",   GPI_DRIVERS   ) < 0 ||
        PyModule_AddIntConstant(simulator, "LOADS",     GPI_LOADS     ) < 0 ||
        false
    ) {
        return -1;
    }

    return 0;
}

// Add the extension types as entries in the module namespace
static int add_module_types(PyObject* simulator)
{
    PyObject *typ;

    typ = (PyObject *)&gpi_hdl_Object<gpi_sim_hdl>::py_type;
    Py_INCREF(typ);
    if (PyModule_AddObject(simulator, "gpi_sim_hdl", typ) < 0) {
        Py_DECREF(typ);
        return -1;
    }

    typ = (PyObject *)&gpi_hdl_Object<gpi_cb_hdl>::py_type;
    Py_INCREF(typ);
    if (PyModule_AddObject(simulator, "gpi_cb_hdl", typ) < 0) {
        Py_DECREF(typ);
        return -1;
    }

    typ = (PyObject *)&gpi_hdl_Object<gpi_iterator_hdl>::py_type;
    Py_INCREF(typ);
    if (PyModule_AddObject(simulator, "gpi_iterator_hdl", typ) < 0) {
        Py_DECREF(typ);
        return -1;
    }

    return 0;
}


/* NOTE: in the following docstrings we are specifying the parameters twice, but this is necessary.
 * The first docstring before the long '--' line specifies the __text_signature__ that is used
 * by the help() function. And the second after the '--' line contains type annotations used by
 * the `autodoc_docstring_signature` setting of sphinx.ext.autodoc for generating documentation
 * because type annotations are not supported in __text_signature__.
 */

static PyMethodDef SimulatorMethods[] = {
    {"log_msg", log_msg, METH_VARARGS, PyDoc_STR(
        "log_msg(name, path, funcname, lineno, msg, /)\n"
        "--\n\n"
        "log_msg(name: str, path: str, funcname: str, lineno: int, msg: str) -> None\n"
        "Log a message."
    )},
    {"get_root_handle", get_root_handle, METH_VARARGS, PyDoc_STR(
        "get_root_handle(name, /)\n"
        "--\n\n"
        "get_root_handle(name: str) -> cocotb.simulator.gpi_sim_hdl\n"
        "Get the root handle."
    )},
    {"register_timed_callback", register_timed_callback, METH_VARARGS, PyDoc_STR(
        "register_timed_callback(time, func, /, *args)\n"
        "--\n\n"
        "register_timed_callback(time: int, func: Callable[..., None], *args: Any) -> cocotb.simulator.gpi_cb_hdl\n"
        "Register a timed callback."
    )},
    {"register_value_change_callback", register_value_change_callback, METH_VARARGS, PyDoc_STR(
        "register_value_change_callback(signal, func, edge, /, *args)\n"
        "--\n\n"
        "register_value_change_callback(signal: cocotb.simulator.gpi_sim_hdl, func: Callable[..., None], edge: int, *args: Any) -> cocotb.simulator.gpi_cb_hdl\n"
        "Register a signal change callback."
    )},
    {"register_readonly_callback", register_readonly_callback, METH_VARARGS, PyDoc_STR(
        "register_readonly_callback(func, /, *args)\n"
        "--\n\n"
        "register_readonly_callback(func: Callable[..., None], *args: Any) -> cocotb.simulator.gpi_cb_hdl\n"
        "Register a callback for the read-only section."
    )},
    {"register_nextstep_callback", register_nextstep_callback, METH_VARARGS, PyDoc_STR(
        "register_nextstep_callback(func, /, *args)\n"
        "--\n\n"
        "register_nextstep_callback(func: Callable[..., None], *args: Any) -> cocotb.simulator.gpi_cb_hdl\n"
        "Register a callback for the cbNextSimTime callback."
    )},
    {"register_rwsynch_callback", register_rwsynch_callback, METH_VARARGS, PyDoc_STR(
        "register_rwsynch_callback(func, /, *args)\n"
        "--\n\n"
        "register_rwsynch_callback(func: Callable[..., None], *args: Any) -> cocotb.simulator.gpi_cb_hdl\n"
        "Register a callback for the read-write section."
    )},
    {"stop_simulator", stop_simulator, METH_VARARGS, PyDoc_STR(
        "stop_simulator()\n"
        "--\n\n"
        "stop_simulator() -> None\n"
        "Instruct the attached simulator to stop. Users should not call this function."
    )},
    {"log_level", log_level, METH_VARARGS, PyDoc_STR(
        "log_level(level, /)\n"
        "--\n\n"
        "log_level(level: int) -> None\n"
        "Set the log level for GPI."
    )},
    {"is_running", is_running, METH_NOARGS, PyDoc_STR(
        "is_running()\n"
        "--\n\n"
        "is_running() -> bool\n"
        "Returns ``True`` if the caller is running within a simulator.\n"
        "\n"
        ".. versionadded:: 1.4"
    )},
    {"get_sim_time", get_sim_time, METH_NOARGS, PyDoc_STR(
        "get_sim_time()\n"
        "--\n\n"
        "get_sim_time() -> Tuple[int, int]\n"
        "Get the current simulation time.\n"
        "\n"
        "Time is represented as a tuple of 32 bit integers ([low32, high32]) comprising a single 64 bit integer."
    )},
    {"get_precision", get_precision, METH_NOARGS, PyDoc_STR(
        "get_precision()\n"
        "--\n\n"
        "get_precision() -> int\n"
        "Get the precision of the simulator in powers of 10.\n"
        "\n"
        "For example, if ``-12`` is returned, the simulator's time precision is 10**-12 or 1 ps."
    )},
    {"get_simulator_product", get_simulator_product, METH_NOARGS, PyDoc_STR(
        "get_simulator_product()\n"
        "--\n\n"
        "get_simulator_product() -> str\n"
        "Get the simulator's product string."
    )},
    {"get_simulator_version", get_simulator_version, METH_NOARGS, PyDoc_STR(
        "get_simulator_version()\n"
        "--\n\n"
        "get_simulator_version() -> str\n"
        "Get the simulator's product version string."
    )},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    MODULE_NAME,
    NULL,
    -1,
    SimulatorMethods,
    NULL,
    NULL,
    NULL,
    NULL
};

#if defined(__linux__) || defined(__APPLE__)
// Only required for Python < 3.9, default for 3.9+ (bpo-11410)
#pragma GCC visibility push(default)
PyMODINIT_FUNC PyInit_simulator(void);
#pragma GCC visibility pop
#endif

PyMODINIT_FUNC PyInit_simulator(void)
{
    /* initialize the extension types */
    if (PyType_Ready(&gpi_hdl_Object<gpi_sim_hdl>::py_type) < 0) {
        return NULL;
    }
    if (PyType_Ready(&gpi_hdl_Object<gpi_cb_hdl>::py_type) < 0) {
        return NULL;
    }
    if (PyType_Ready(&gpi_hdl_Object<gpi_iterator_hdl>::py_type) < 0) {
        return NULL;
    }

    PyObject* simulator = PyModule_Create(&moduledef);
    if (simulator == NULL) {
        return NULL;
    }

    if (add_module_constants(simulator) < 0) {
        Py_DECREF(simulator);
        return NULL;
    }

    if (add_module_types(simulator) < 0) {
        Py_DECREF(simulator);
        return NULL;
    }

    return simulator;
}

/* NOTE: in the following docstrings we are specifying the parameters twice, but this is necessary.
 * The first docstring before the long '--' line specifies the __text_signature__ that is used
 * by the help() function. And the second after the '--' line contains type annotations used by
 * the `autodoc_docstring_signature` setting of sphinx.ext.autodoc for generating documentation
 * because type annotations are not supported in __text_signature__.
 */

static PyMethodDef gpi_sim_hdl_methods[] = {
    {"get_signal_val_long",
        (PyCFunction)get_signal_val_long, METH_NOARGS, PyDoc_STR(
            "get_signal_val_long($self)\n"
            "--\n\n"
            "get_signal_val_long() -> int\n"
            "Get the value of a signal as an integer."
        )
    },
    {"get_signal_val_str",
        (PyCFunction)get_signal_val_str, METH_NOARGS, PyDoc_STR(
            "get_signal_val_str($self)\n"
            "--\n\n"
            "get_signal_val_str() -> bytes\n"
            "Get the value of a signal as a byte string."
        )
    },
    {"get_signal_val_binstr",
        (PyCFunction)get_signal_val_binstr, METH_NOARGS, PyDoc_STR(
            "get_signal_val_binstr($self)\n"
            "--\n\n"
            "get_signal_val_binstr() -> str\n"
            "Get the value of a logic vector signal as a string of (``0``, ``1``, ``X``, etc.), one element per character."
        )
    },
    {"get_signal_val_real",
        (PyCFunction)get_signal_val_real, METH_NOARGS, PyDoc_STR(
            "get_signal_val_real($self)\n"
            "--\n\n"
            "get_signal_val_real() -> float\n"
            "Get the value of a signal as a float."
        )
    },
    {"set_signal_val_int",
        (PyCFunction)set_signal_val_int, METH_VARARGS, PyDoc_STR(
            "set_signal_val_int($self, action, value, /)\n"
            "--\n\n"
            "Set the value of a signal using an int"
        )
    },
    {"set_signal_val_str",
        (PyCFunction)set_signal_val_str, METH_VARARGS, PyDoc_STR(
            "set_signal_val_str($self, action, value, /)\n"
            "--\n\n"
            "set_signal_val_str(action: int, value: bytes) -> None\n"
            "Set the value of a signal using a user-encoded string."
        )
    },
    {"set_signal_val_binstr",
        (PyCFunction)set_signal_val_binstr, METH_VARARGS, PyDoc_STR(
            "set_signal_val_binstr($self, action, value, /)\n"
            "--\n\n"
            "set_signal_val_binstr(action: int, value: str) -> None\n"
            "Set the value of a logic vector signal using a string of (``0``, ``1``, ``X``, etc.), one element per character."
        )
    },
    {"set_signal_val_real",
        (PyCFunction)set_signal_val_real, METH_VARARGS, PyDoc_STR(
            "set_signal_val_real($self, action, value, /)\n"
            "--\n\n"
            "set_signal_val_real(action: int, value: float) -> None\n"
            "Set the value of a signal using a float."
        )
    },
    {"get_definition_name",
        (PyCFunction)get_definition_name, METH_NOARGS, PyDoc_STR(
            "get_definition_name($self)\n"
            "--\n\n"
            "get_definition_name() -> str\n"
            "Get the name of a GPI object's definition."
        )
    },
    {"get_definition_file",
        (PyCFunction)get_definition_file, METH_NOARGS, PyDoc_STR(
            "get_definition_file($self)\n"
            "--\n\n"
            "get_definition_file() -> str\n"
            "Get the file that sources the object's definition."
        )
    },
    {"get_handle_by_name",
        (PyCFunction)get_handle_by_name, METH_VARARGS, PyDoc_STR(
            "get_handle_by_name($self, name, /)\n"
            "--\n\n"
            "get_handle_by_name(name: str) -> cocotb.simulator.gpi_sim_hdl\n"
            "Get a handle to a child object by name."
        )
    },
    {"get_handle_by_index",
        (PyCFunction)get_handle_by_index, METH_VARARGS, PyDoc_STR(
            "get_handle_by_index($self, index, /)\n"
            "--\n\n"
            "get_handle_by_index(index: int) -> cocotb.simulator.gpi_sim_hdl\n"
            "Get a handle to a child object by index."
        )
    },
    {"get_name_string",
        (PyCFunction)get_name_string, METH_NOARGS, PyDoc_STR(
            "get_name_string($self)\n"
            "--\n\n"
            "get_name_string() -> str\n"
            "Get the name of an object as a string."
        )
    },
    {"get_type_string",
        (PyCFunction)get_type_string, METH_NOARGS, PyDoc_STR(
            "get_type_string($self)\n"
            "--\n\n"
            "get_type_string() -> str\n"
            "Get the GPI type of an object as a string."
        )
    },
    {"get_type",
        (PyCFunction)get_type, METH_NOARGS, PyDoc_STR(
            "get_type($self)\n"
            "--\n\n"
            "get_type() -> int\n"
            "Get the GPI type of an object as an enum."
        )
    },
    {"get_const",
        (PyCFunction)get_const, METH_NOARGS, PyDoc_STR(
            "get_const($self)\n"
            "--\n\n"
            "get_const() -> bool\n"
            "Return ``True`` if the object is a constant."
        )
    },
    {"get_num_elems",
        (PyCFunction)get_num_elems, METH_NOARGS, PyDoc_STR(
            "get_num_elems($self)\n"
            "--\n\n"
            "get_num_elems() -> int\n"
            "Get the number of elements contained in the handle."
        )
    },
    {"get_range",
        (PyCFunction)get_range, METH_NOARGS, PyDoc_STR(
            "get_range($self)\n"
            "--\n\n"
            "get_range() -> Tuple[int, int]\n"
            "Get the range of elements (tuple) contained in the handle, return ``None`` if not indexable."
        )
    },
    {"iterate",
        (PyCFunction)iterate, METH_VARARGS, PyDoc_STR(
            "iterate($self, mode, /)\n"
            "--\n\n"
            "iterate(mode: int) -> cocotb.simulator.gpi_iterator_hdl\n"
            "Get an iterator handle to loop over all members in an object."
        )
    },
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

// putting these at the bottom means that all the functions above are accessible
template<>
PyTypeObject gpi_hdl_Object<gpi_sim_hdl>::py_type = []() -> PyTypeObject {
    auto type = fill_common_slots<gpi_sim_hdl>();
    type.tp_name = "cocotb.simulator.gpi_sim_hdl";
    type.tp_doc = "GPI object handle\n"
        "\n"
        "Contains methods for getting and setting the value of a GPI object, and introspection.";
    type.tp_methods = gpi_sim_hdl_methods;
    return type;
}();

template<>
PyTypeObject gpi_hdl_Object<gpi_iterator_hdl>::py_type = []() -> PyTypeObject {
    auto type = fill_common_slots<gpi_iterator_hdl>();
    type.tp_name = "cocotb.simulator.gpi_iterator_hdl";
    type.tp_doc = "GPI iterator handle.";
    type.tp_iter = PyObject_SelfIter;
    type.tp_iternext = (iternextfunc)next;
    return type;
}();

static PyMethodDef gpi_cb_hdl_methods[] = {
    {"deregister",
        (PyCFunction)deregister, METH_NOARGS, PyDoc_STR(
            "deregister($self)\n"
            "--\n\n"
            "deregister() -> None\n"
            "De-register this callback."
        )},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

template<>
PyTypeObject gpi_hdl_Object<gpi_cb_hdl>::py_type = []() -> PyTypeObject {
    auto type = fill_common_slots<gpi_cb_hdl>();
    type.tp_name = "cocotb.simulator.gpi_cb_hdl";
    type.tp_doc = "GPI callback handle";
    type.tp_methods = gpi_cb_hdl_methods;
    return type;
}();
