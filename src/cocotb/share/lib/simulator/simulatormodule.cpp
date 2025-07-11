// Copyright cocotb contributors
// Copyright (c) 2013, 2018 Potential Ventures Ltd
// Copyright (c) 2013 SolarFlare Communications Inc
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

/**
 * @file   simulatormodule.cpp
 * @brief Python extension to provide access to the simulator
 *
 * Uses GPI calls to interface to the simulator.
 */

#include <Python.h>

#include <cerrno>
#include <cstdint>

#include "cocotb_utils.h"  // to_python to_simulator
#include "gpi.h"
#include "py_gpi_logging.h"  // py_gpi_logger_set_level

// This file defines the routines available to Python

#define MODULE_NAME "simulator"

// callback user data
struct PythonCallback {
    PythonCallback(PyObject *func, PyObject *_args, PyObject *_kwargs)
        : function(func), args(_args), kwargs(_kwargs) {
        Py_XINCREF(function);
        Py_XINCREF(args);
        Py_XINCREF(kwargs);
    }
    ~PythonCallback() {
        Py_XDECREF(function);
        Py_XDECREF(args);
        Py_XDECREF(kwargs);
    }
    intptr_t padding_;   // TODO exists to works around bug with FLI
    PyObject *function;  // Function to call when the callback fires
    PyObject *args;      // The arguments to call the function with
    PyObject *kwargs;    // Keyword arguments to call the function with
};

class GpiClock;
using gpi_clk_hdl = GpiClock *;

/* define the extension types as templates */
namespace {
template <typename gpi_hdl>
struct gpi_hdl_Object {
    PyObject_HEAD gpi_hdl hdl;

    // The python type object, in a place that is easy to retrieve in templates
    static PyTypeObject py_type;
};

/** __repr__ shows the memory address of the internal handle */
template <typename gpi_hdl>
static PyObject *gpi_hdl_repr(gpi_hdl_Object<gpi_hdl> *self) {
    auto *type = Py_TYPE(self);
    return PyUnicode_FromFormat("<%s at %p>", type->tp_name, self->hdl);
}

/** __hash__ returns the pointer itself */
template <typename gpi_hdl>
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
template <typename gpi_hdl>
static PyObject *gpi_hdl_New(gpi_hdl hdl) {
    if (hdl == NULL) {
        Py_RETURN_NONE;
    }
    auto *obj = PyObject_New(gpi_hdl_Object<gpi_hdl>,
                             &gpi_hdl_Object<gpi_hdl>::py_type);
    if (obj == NULL) {
        return NULL;
    }
    obj->hdl = hdl;
    return (PyObject *)obj;
}

/** Comparison checks if the types match, and then compares pointers */
template <typename gpi_hdl>
static PyObject *gpi_hdl_richcompare(PyObject *self, PyObject *other, int op) {
    if (Py_TYPE(self) != &gpi_hdl_Object<gpi_hdl>::py_type ||
        Py_TYPE(other) != &gpi_hdl_Object<gpi_hdl>::py_type) {
        Py_RETURN_NOTIMPLEMENTED;
    }

    auto self_hdl_obj = reinterpret_cast<gpi_hdl_Object<gpi_hdl> *>(self);
    auto other_hdl_obj = reinterpret_cast<gpi_hdl_Object<gpi_hdl> *>(other);

    switch (op) {
        case Py_EQ:
            return PyBool_FromLong(self_hdl_obj->hdl == other_hdl_obj->hdl);
        case Py_NE:
            return PyBool_FromLong(self_hdl_obj->hdl != other_hdl_obj->hdl);
        default:
            Py_RETURN_NOTIMPLEMENTED;
    }
}

// Initialize the Python type slots
template <typename gpi_hdl>
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
template <>
PyTypeObject gpi_hdl_Object<gpi_sim_hdl>::py_type;
template <>
PyTypeObject gpi_hdl_Object<gpi_iterator_hdl>::py_type;
template <>
PyTypeObject gpi_hdl_Object<gpi_cb_hdl>::py_type;
template <>
PyTypeObject gpi_hdl_Object<gpi_clk_hdl>::py_type;
}  // namespace

typedef int (*gpi_function_t)(void *);

struct sim_time {
    uint32_t high;
    uint32_t low;
};

/**
 * @name    Callback Handling
 * @brief   Handle a callback coming from GPI
 * @ingroup python_c_api
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
 */
int handle_gpi_callback(void *user_data) {
    to_python();
    DEFER(to_simulator());

    PyGILState_STATE gstate = PyGILState_Ensure();
    DEFER(PyGILState_Release(gstate));

    PythonCallback *cb_data = (PythonCallback *)user_data;
    DEFER(delete cb_data);

    // Call the callback
    PyObject *pValue =
        PyObject_Call(cb_data->function, cb_data->args, cb_data->kwargs);

    // If the return value is NULL a Python exception has occurred
    // The best thing to do here is shutdown as any subsequent
    // calls will go back to Python which is now in an unknown state
    if (pValue == NULL) {
        // Printing a SystemExit calls exit(1), which we don't want.
        if (!PyErr_ExceptionMatches(PyExc_SystemExit)) {
            PyErr_Print();
        }
        // Clear error so re-entering Python doesn't fail.
        PyErr_Clear();
        return -1;
    }

    // We don't care about the result
    Py_DECREF(pValue);

    return 0;
}

// Register a callback for read-only state of sim
// First argument is the function to call
// Remaining arguments are keyword arguments to be passed to the callback
static PyObject *register_readonly_callback(PyObject *, PyObject *args) {
    if (!gpi_has_registered_impl()) {
        PyErr_SetString(PyExc_RuntimeError, "No simulator available!");
        return NULL;
    }

    Py_ssize_t numargs = PyTuple_Size(args);

    if (numargs < 1) {
        PyErr_SetString(PyExc_TypeError,
                        "Attempt to register ReadOnly callback without enough "
                        "arguments!\n");
        return NULL;
    }

    // Extract the callback function
    PyObject *function = PyTuple_GetItem(args, 0);  // borrow reference
    if (!PyCallable_Check(function)) {
        PyErr_SetString(
            PyExc_TypeError,
            "Attempt to register ReadOnly without supplying a callback!\n");
        return NULL;
    }

    // Remaining args for function
    PyObject *fArgs = PyTuple_GetSlice(args, 1, numargs);  // New reference
    if (fArgs == NULL) {
        return NULL;
    }
    DEFER(Py_DECREF(fArgs));

    PythonCallback *cb_data = new PythonCallback(function, fArgs, NULL);

    gpi_cb_hdl hdl = gpi_register_readonly_callback(
        (gpi_function_t)handle_gpi_callback, cb_data);

    PyObject *rv = gpi_hdl_New(hdl);

    return rv;
}

static PyObject *register_rwsynch_callback(PyObject *, PyObject *args) {
    if (!gpi_has_registered_impl()) {
        PyErr_SetString(PyExc_RuntimeError, "No simulator available!");
        return NULL;
    }

    Py_ssize_t numargs = PyTuple_Size(args);

    if (numargs < 1) {
        PyErr_SetString(PyExc_TypeError,
                        "Attempt to register ReadWrite callback without enough "
                        "arguments!\n");
        return NULL;
    }

    // Extract the callback function
    PyObject *function = PyTuple_GetItem(args, 0);  // borrow reference
    if (!PyCallable_Check(function)) {
        PyErr_SetString(
            PyExc_TypeError,
            "Attempt to register ReadWrite without supplying a callback!\n");
        return NULL;
    }

    // Remaining args for function
    PyObject *fArgs = PyTuple_GetSlice(args, 1, numargs);  // New reference
    if (fArgs == NULL) {
        return NULL;
    }
    DEFER(Py_DECREF(fArgs));

    PythonCallback *cb_data = new PythonCallback(function, fArgs, NULL);

    gpi_cb_hdl hdl = gpi_register_readwrite_callback(
        (gpi_function_t)handle_gpi_callback, cb_data);

    PyObject *rv = gpi_hdl_New(hdl);

    return rv;
}

static PyObject *register_nextstep_callback(PyObject *, PyObject *args) {
    if (!gpi_has_registered_impl()) {
        PyErr_SetString(PyExc_RuntimeError, "No simulator available!");
        return NULL;
    }

    Py_ssize_t numargs = PyTuple_Size(args);

    if (numargs < 1) {
        PyErr_SetString(PyExc_TypeError,
                        "Attempt to register NextStep callback without enough "
                        "arguments!\n");
        return NULL;
    }

    // Extract the callback function
    PyObject *function = PyTuple_GetItem(args, 0);  // borrow reference
    if (!PyCallable_Check(function)) {
        PyErr_SetString(
            PyExc_TypeError,
            "Attempt to register NextStep without supplying a callback!\n");
        return NULL;
    }

    // Remaining args for function
    PyObject *fArgs = PyTuple_GetSlice(args, 1, numargs);  // New reference
    if (fArgs == NULL) {
        return NULL;
    }
    DEFER(Py_DECREF(fArgs));

    PythonCallback *cb_data = new PythonCallback(function, fArgs, NULL);

    gpi_cb_hdl hdl = gpi_register_nexttime_callback(
        (gpi_function_t)handle_gpi_callback, cb_data);

    PyObject *rv = gpi_hdl_New(hdl);

    return rv;
}

// Register a timed callback.
// First argument should be the time in picoseconds
// Second argument is the function to call
// Remaining arguments and keyword arguments are to be passed to the callback
static PyObject *register_timed_callback(PyObject *, PyObject *args) {
    if (!gpi_has_registered_impl()) {
        PyErr_SetString(PyExc_RuntimeError, "No simulator available!");
        return NULL;
    }

    Py_ssize_t numargs = PyTuple_Size(args);

    if (numargs < 2) {
        PyErr_SetString(
            PyExc_TypeError,
            "Attempt to register timed callback without enough arguments!\n");
        return NULL;
    }

    uint64_t time;
    {  // Extract the time
        PyObject *pTime = PyTuple_GetItem(args, 0);
        long long pTime_as_longlong = PyLong_AsLongLong(pTime);
        if (pTime_as_longlong == -1 && PyErr_Occurred()) {
            return NULL;
        } else if (pTime_as_longlong < 0) {
            PyErr_SetString(PyExc_ValueError,
                            "Timer value must be a positive integer");
            return NULL;
        } else {
            time = (uint64_t)pTime_as_longlong;
        }
    }

    // Extract the callback function
    PyObject *function = PyTuple_GetItem(args, 1);  // borrow reference
    if (!PyCallable_Check(function)) {
        PyErr_SetString(PyExc_TypeError,
                        "Attempt to register timed callback without passing a "
                        "callable callback!\n");
        return NULL;
    }

    // Remaining args for function
    PyObject *fArgs = PyTuple_GetSlice(args, 2, numargs);  // New reference
    if (fArgs == NULL) {
        return NULL;
    }
    DEFER(Py_DECREF(fArgs));

    PythonCallback *cb_data = new PythonCallback(function, fArgs, NULL);

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
static PyObject *register_value_change_callback(
    PyObject *, PyObject *args)  //, PyObject *keywds)
{
    if (!gpi_has_registered_impl()) {
        PyErr_SetString(PyExc_RuntimeError, "No simulator available!");
        return NULL;
    }

    Py_ssize_t numargs = PyTuple_Size(args);

    if (numargs < 3) {
        PyErr_SetString(PyExc_TypeError,
                        "Attempt to register value change callback without "
                        "enough arguments!\n");
        return NULL;
    }

    PyObject *pSigHdl = PyTuple_GetItem(args, 0);
    if (Py_TYPE(pSigHdl) != &gpi_hdl_Object<gpi_sim_hdl>::py_type) {
        PyErr_SetString(PyExc_TypeError,
                        "First argument must be a gpi_sim_hdl");
        return NULL;
    }
    gpi_sim_hdl sig_hdl = ((gpi_hdl_Object<gpi_sim_hdl> *)pSigHdl)->hdl;

    // Extract the callback function
    PyObject *function = PyTuple_GetItem(args, 1);  // borrow reference
    if (!PyCallable_Check(function)) {
        PyErr_SetString(PyExc_TypeError,
                        "Attempt to register value change callback without "
                        "passing a callable callback!\n");
        return NULL;
    }

    PyObject *pedge = PyTuple_GetItem(args, 2);  // borrow reference
    gpi_edge edge = (gpi_edge)PyLong_AsLong(pedge);

    // Remaining args for function
    PyObject *fArgs = PyTuple_GetSlice(args, 3, numargs);  // New reference
    if (fArgs == NULL) {
        return NULL;
    }
    DEFER(Py_DECREF(fArgs));

    PythonCallback *cb_data = new PythonCallback(function, fArgs, NULL);

    gpi_cb_hdl hdl = gpi_register_value_change_callback(
        (gpi_function_t)handle_gpi_callback, cb_data, sig_hdl, edge);

    // Check success
    PyObject *rv = gpi_hdl_New(hdl);

    return rv;
}

static PyObject *iterate(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *args) {
    int type;

    if (!PyArg_ParseTuple(args, "i:iterate", &type)) {
        return NULL;
    }

    gpi_iterator_hdl result = gpi_iterate(self->hdl, (gpi_iterator_sel)type);

    return gpi_hdl_New(result);
}

static PyObject *package_iterate(PyObject *, PyObject *) {
    gpi_iterator_hdl result = gpi_iterate(NULL, GPI_PACKAGE_SCOPES);

    return gpi_hdl_New(result);
}

static PyObject *next(gpi_hdl_Object<gpi_iterator_hdl> *self) {
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

static PyObject *get_signal_val_binstr(gpi_hdl_Object<gpi_sim_hdl> *self,
                                       PyObject *) {
    const char *result = gpi_get_signal_value_binstr(self->hdl);
    if (result == NULL) {
        // LCOV_EXCL_START
        PyErr_SetString(PyExc_RuntimeError,
                        "Simulator yielded a null pointer instead of binstr");
        return NULL;
        // LCOV_EXCL_STOP
    }
    return PyUnicode_FromString(result);
}

static PyObject *get_signal_val_str(gpi_hdl_Object<gpi_sim_hdl> *self,
                                    PyObject *) {
    const char *result = gpi_get_signal_value_str(self->hdl);
    if (result == NULL) {
        // LCOV_EXCL_START
        PyErr_SetString(PyExc_RuntimeError,
                        "Simulator yielded a null pointer instead of string");
        return NULL;
        // LCOV_EXCL_STOP
    }
    return PyBytes_FromString(result);
}

static PyObject *get_signal_val_real(gpi_hdl_Object<gpi_sim_hdl> *self,
                                     PyObject *) {
    double result = gpi_get_signal_value_real(self->hdl);
    return PyFloat_FromDouble(result);
}

static PyObject *get_signal_val_long(gpi_hdl_Object<gpi_sim_hdl> *self,
                                     PyObject *) {
    long result = gpi_get_signal_value_long(self->hdl);
    return PyLong_FromLong(result);
}

static PyObject *set_signal_val_binstr(gpi_hdl_Object<gpi_sim_hdl> *self,
                                       PyObject *args) {
    const char *binstr;
    gpi_set_action action;

    if (!PyArg_ParseTuple(args, "is:set_signal_val_binstr", &action, &binstr)) {
        return NULL;
    }

    gpi_set_signal_value_binstr(self->hdl, binstr, action);
    Py_RETURN_NONE;
}

static PyObject *set_signal_val_str(gpi_hdl_Object<gpi_sim_hdl> *self,
                                    PyObject *args) {
    gpi_set_action action;
    const char *str;

    if (!PyArg_ParseTuple(args, "iy:set_signal_val_str", &action, &str)) {
        return NULL;
    }

    gpi_set_signal_value_str(self->hdl, str, action);
    Py_RETURN_NONE;
}

static PyObject *set_signal_val_real(gpi_hdl_Object<gpi_sim_hdl> *self,
                                     PyObject *args) {
    double value;
    gpi_set_action action;

    if (!PyArg_ParseTuple(args, "id:set_signal_val_real", &action, &value)) {
        return NULL;
    }

    gpi_set_signal_value_real(self->hdl, value, action);
    Py_RETURN_NONE;
}

static PyObject *set_signal_val_int(gpi_hdl_Object<gpi_sim_hdl> *self,
                                    PyObject *args) {
    long long value;
    gpi_set_action action;

    if (!PyArg_ParseTuple(args, "iL:set_signal_val_int", &action, &value)) {
        return NULL;
    }

    gpi_set_signal_value_int(self->hdl, static_cast<int32_t>(value), action);
    Py_RETURN_NONE;
}

static PyObject *get_definition_name(gpi_hdl_Object<gpi_sim_hdl> *self,
                                     PyObject *) {
    const char *result = gpi_get_definition_name(self->hdl);
    return PyUnicode_FromString(result);
}

static PyObject *get_definition_file(gpi_hdl_Object<gpi_sim_hdl> *self,
                                     PyObject *) {
    const char *result = gpi_get_definition_file(self->hdl);
    return PyUnicode_FromString(result);
}

static PyObject *get_handle_by_name(gpi_hdl_Object<gpi_sim_hdl> *self,
                                    PyObject *args) {
    const char *name;
    // if unset, we assume AUTO, which maintains backward-compatibility
    int py_discovery_method = 0;
    gpi_discovery c_discovery_method = GPI_AUTO;

    if (!PyArg_ParseTuple(args, "s|i:get_handle_by_name", &name,
                          &py_discovery_method)) {
        return NULL;
    }
    // do some additional input validation, then map to enum
    if (py_discovery_method < 0 || py_discovery_method > 1) {
        PyErr_SetString(PyExc_ValueError,
                        "Enum value for discovery_method out of range");
        return NULL;
    } else {
        c_discovery_method = (gpi_discovery)py_discovery_method;
    }

    gpi_sim_hdl result =
        gpi_get_handle_by_name(self->hdl, name, c_discovery_method);

    return gpi_hdl_New(result);
}

static PyObject *get_handle_by_index(gpi_hdl_Object<gpi_sim_hdl> *self,
                                     PyObject *args) {
    int32_t index;

    if (!PyArg_ParseTuple(args, "i:get_handle_by_index", &index)) {
        return NULL;
    }

    gpi_sim_hdl result = gpi_get_handle_by_index(self->hdl, index);

    return gpi_hdl_New(result);
}

static PyObject *get_root_handle(PyObject *, PyObject *args) {
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

static PyObject *get_name_string(gpi_hdl_Object<gpi_sim_hdl> *self,
                                 PyObject *) {
    const char *result = gpi_get_signal_name_str(self->hdl);
    return PyUnicode_FromString(result);
}

static PyObject *get_type(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *) {
    gpi_objtype result = gpi_get_object_type(self->hdl);
    return PyLong_FromLong(result);
}

static PyObject *get_const(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *) {
    int result = gpi_is_constant(self->hdl);
    return PyBool_FromLong(result);
}

static PyObject *get_type_string(gpi_hdl_Object<gpi_sim_hdl> *self,
                                 PyObject *) {
    const char *result = gpi_get_signal_type_str(self->hdl);
    return PyUnicode_FromString(result);
}

static PyObject *is_running(PyObject *, PyObject *) {
    return PyBool_FromLong(gpi_has_registered_impl());
}

// Returns a high, low, tuple of simulator time
// Note we can never log from this function since the logging mechanism calls
// this to annotate log messages with the current simulation time
static PyObject *get_sim_time(PyObject *, PyObject *) {
    if (!gpi_has_registered_impl()) {
        PyErr_SetString(PyExc_RuntimeError, "No simulator available!");
        return NULL;
    }

    struct sim_time local_time;

    gpi_get_sim_time(&local_time.high, &local_time.low);

    PyObject *pTuple = PyTuple_New(2);
    PyTuple_SetItem(
        pTuple, 0,
        PyLong_FromUnsignedLong(
            local_time
                .high));  // Note: This function “steals” a reference to o.
    PyTuple_SetItem(
        pTuple, 1,
        PyLong_FromUnsignedLong(
            local_time.low));  // Note: This function “steals” a reference to o.

    return pTuple;
}

static PyObject *get_precision(PyObject *, PyObject *) {
    if (!gpi_has_registered_impl()) {
        char const *msg =
            "Simulator is not available! Defaulting precision to 1 fs.";
        if (PyErr_WarnEx(PyExc_RuntimeWarning, msg, 1) < 0) {
            return NULL;
        }
        return PyLong_FromLong(-15);  // preserves old behavior
    }

    int32_t precision;

    gpi_get_sim_precision(&precision);

    return PyLong_FromLong(precision);
}

static PyObject *get_simulator_product(PyObject *, PyObject *) {
    if (!gpi_has_registered_impl()) {
        PyErr_SetString(PyExc_RuntimeError, "No simulator available!");
        return NULL;
    }

    return PyUnicode_FromString(gpi_get_simulator_product());
}

static PyObject *get_simulator_version(PyObject *, PyObject *) {
    if (!gpi_has_registered_impl()) {
        PyErr_SetString(PyExc_RuntimeError, "No simulator available!");
        return NULL;
    }

    return PyUnicode_FromString(gpi_get_simulator_version());
}

static PyObject *get_num_elems(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *) {
    int elems = gpi_get_num_elems(self->hdl);
    return PyLong_FromLong(elems);
}

static PyObject *get_range(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *) {
    int rng_left = gpi_get_range_left(self->hdl);
    int rng_right = gpi_get_range_right(self->hdl);
    int rng_dir = gpi_get_range_dir(self->hdl);

    return Py_BuildValue("(i,i,i)", rng_left, rng_right, rng_dir);
}

static PyObject *get_indexable(gpi_hdl_Object<gpi_sim_hdl> *self, PyObject *) {
    int indexable = gpi_is_indexable(self->hdl);

    return PyBool_FromLong(indexable);
}

static PyObject *stop_simulator(PyObject *, PyObject *) {
    if (!gpi_has_registered_impl()) {
        PyErr_SetString(PyExc_RuntimeError, "No simulator available!");
        return NULL;
    }

    gpi_sim_end();
    Py_RETURN_NONE;
}

static PyObject *deregister(gpi_hdl_Object<gpi_cb_hdl> *self, PyObject *) {
    // cleanup uncalled callback
    void *cb_data;
    gpi_get_cb_info(self->hdl, nullptr, &cb_data);
    auto cb = static_cast<PythonCallback *>(cb_data);
    delete cb;

    // deregister from interface
    gpi_remove_cb(self->hdl);

    Py_RETURN_NONE;
}

static PyObject *set_gpi_log_level(PyObject *, PyObject *args) {
    int l_level;

    if (!PyArg_ParseTuple(args, "i:log_level", &l_level)) {
        return NULL;
    }

    gpi_log_set_level("gpi", l_level);

    Py_RETURN_NONE;
}

static PyObject *initialize_logger(PyObject *, PyObject *args) {
    PyObject *log_func;
    PyObject *get_logger;
    if (!PyArg_ParseTuple(args, "OO", &log_func, &get_logger)) {
        PyErr_Print();
        return NULL;
    }
    py_gpi_logger_initialize(log_func, get_logger);
    Py_RETURN_NONE;
}

static PyObject *set_sim_event_callback(PyObject *, PyObject *args) {
    if (pEventFn) {
        PyErr_SetString(PyExc_RuntimeError,
                        "Simulator event callback already set!");
        return NULL;
    }

    PyObject *sim_event_callback;
    if (!PyArg_ParseTuple(args, "O", &sim_event_callback)) {
        PyErr_Print();
        Py_RETURN_NONE;
    }
    Py_INCREF(sim_event_callback);
    pEventFn = sim_event_callback;
    Py_RETURN_NONE;
}

class GpiClock {
  public:
    GpiClock(GpiObjHdl *clk_sig) : clk_signal(clk_sig) {}

    ~GpiClock() { stop(); }

    // Start the clock. Returns nonzero in case of failure:
    //  - EBUSY if the clock was already started (stop first)
    //  - EINVAL if the parameters are invalid
    //  - EAGAIN if registering the toggle callback failed
    int start(uint64_t period_steps, uint64_t high_steps, bool start_high,
              gpi_set_action set_action);

    int stop();

  private:
    GpiObjHdl *clk_signal = nullptr;
    GpiCbHdl *clk_toggle_cb_hdl = nullptr;

    uint64_t period = 0;
    uint64_t t_high = 0;
    gpi_set_action m_set_action;

    int clk_val = 0;

    int toggle(bool initialSet);
    static int toggle_cb(void *gpi_clk);
};

int GpiClock::start(uint64_t period_steps, uint64_t high_steps, bool start_high,
                    gpi_set_action set_action) {
    if (clk_toggle_cb_hdl) {
        return EBUSY;
    }
    if ((period_steps < 2) || (high_steps < 1) ||
        (high_steps >= period_steps)) {
        return EINVAL;
    }

    period = period_steps;
    t_high = high_steps;
    m_set_action = set_action;

    clk_val = start_high;
    return toggle(true);
}

int GpiClock::stop() {
    if (!clk_toggle_cb_hdl) {
        return -1;
    }
    gpi_remove_cb(clk_toggle_cb_hdl);
    clk_toggle_cb_hdl = nullptr;
    return 0;
}

int GpiClock::toggle(bool initialSet) {
    if (!initialSet) {
        clk_val = !clk_val;
    }
    gpi_set_signal_value_int(clk_signal, clk_val, m_set_action);

    uint64_t to_next_edge = clk_val ? t_high : (period - t_high);

    clk_toggle_cb_hdl =
        gpi_register_timed_callback(&GpiClock::toggle_cb, this, to_next_edge);
    if (!clk_toggle_cb_hdl) {
        // LCOV_EXCL_START
        if (!initialSet) {
            // Failing when called from start() will be reported via
            // exception, but log in case of later failure that would
            // otherwise be silent.
            LOG_ERROR("Clock will be stopped: failed to register toggle cb");
        }
        return EAGAIN;
        // LCOV_EXCL_STOP
    }

    return 0;
}

int GpiClock::toggle_cb(void *gpi_clk) {
    GpiClock *clk_obj = (GpiClock *)gpi_clk;
    return clk_obj->toggle(false);
}

// Create a new clock object
static PyObject *clock_create(PyObject *, PyObject *args) {
    if (!gpi_has_registered_impl()) {
        // LCOV_EXCL_START
        PyErr_SetString(PyExc_RuntimeError, "No simulator available!");
        return NULL;
        // LCOV_EXCL_STOP
    }

    // Extract the clock signal sim object
    PyObject *pSigHdl;
    if (!PyArg_ParseTuple(args, "O!:clock_create",
                          &gpi_hdl_Object<gpi_sim_hdl>::py_type, &pSigHdl)) {
        return NULL;
    }
    gpi_sim_hdl sim_hdl = ((gpi_hdl_Object<gpi_sim_hdl> *)pSigHdl)->hdl;

    GpiClock *gpi_clk = new GpiClock(sim_hdl);

    if (gpi_clk) {
        return gpi_hdl_New(gpi_clk);
    } else {
        // LCOV_EXCL_START
        PyErr_SetString(PyExc_RuntimeError, "Failed to create clock!");
        return NULL;
        // LCOV_EXCL_STOP
    }
}

static void clock_dealloc(PyObject *self) {
    if (!gpi_has_registered_impl()) {
        // LCOV_EXCL_START
        PyErr_SetString(PyExc_RuntimeError, "No simulator available!");
        return;
        // LCOV_EXCL_STOP
    }

    if (Py_TYPE(self) != &gpi_hdl_Object<gpi_clk_hdl>::py_type) {
        // LCOV_EXCL_START
        PyErr_SetString(PyExc_TypeError, "Wrong type for clock_dealloc!");
        return;
        // LCOV_EXCL_STOP
    }

    GpiClock *gpi_clk = ((gpi_hdl_Object<gpi_clk_hdl> *)self)->hdl;

    delete gpi_clk;

    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyObject *clk_start(gpi_hdl_Object<gpi_clk_hdl> *self, PyObject *args) {
    unsigned long long period, t_high;
    int start_high;
    int set_action;

    if (!PyArg_ParseTuple(args, "KKpi:start", &period, &t_high, &start_high,
                          &set_action)) {
        return NULL;
    }

    int ret = self->hdl->start(period, t_high, start_high,
                               (gpi_set_action)set_action);

    if (ret != 0) {
        if (ret == EINVAL) {
            PyErr_SetString(PyExc_ValueError,
                            "Failed to start clock: invalid arguments!\n");
        } else if (ret == EBUSY) {
            PyErr_SetString(PyExc_RuntimeError,
                            "Failed to start clock: already started!\n");
        } else {
            // LCOV_EXCL_START
            PyErr_SetString(PyExc_RuntimeError, "Failed to start clock!\n");
            // LCOV_EXCL_STOP
        }
        return NULL;
    }

    Py_RETURN_NONE;
}

static PyObject *clk_stop(gpi_hdl_Object<gpi_clk_hdl> *self, PyObject *) {
    self->hdl->stop();

    Py_RETURN_NONE;
}

static int add_module_constants(PyObject *simulator) {
    // Make the GPI constants accessible from the C world
    if (PyModule_AddIntConstant(simulator, "UNKNOWN", GPI_UNKNOWN) < 0 ||
        PyModule_AddIntConstant(simulator, "MEMORY", GPI_MEMORY) < 0 ||
        PyModule_AddIntConstant(simulator, "MODULE", GPI_MODULE) < 0 ||
        PyModule_AddIntConstant(simulator, "NETARRAY", GPI_ARRAY) < 0 ||
        PyModule_AddIntConstant(simulator, "ENUM", GPI_ENUM) < 0 ||
        PyModule_AddIntConstant(simulator, "STRUCTURE", GPI_STRUCTURE) < 0 ||
        PyModule_AddIntConstant(simulator, "PACKED_STRUCTURE",
                                GPI_PACKED_STRUCTURE) < 0 ||
        PyModule_AddIntConstant(simulator, "REAL", GPI_REAL) < 0 ||
        PyModule_AddIntConstant(simulator, "INTEGER", GPI_INTEGER) < 0 ||
        PyModule_AddIntConstant(simulator, "STRING", GPI_STRING) < 0 ||
        PyModule_AddIntConstant(simulator, "GENARRAY", GPI_GENARRAY) < 0 ||
        PyModule_AddIntConstant(simulator, "PACKAGE", GPI_PACKAGE) < 0 ||
        PyModule_AddIntConstant(simulator, "OBJECTS", GPI_OBJECTS) < 0 ||
        PyModule_AddIntConstant(simulator, "DRIVERS", GPI_DRIVERS) < 0 ||
        PyModule_AddIntConstant(simulator, "LOADS", GPI_LOADS) < 0 ||
        PyModule_AddIntConstant(simulator, "RISING", GPI_RISING) < 0 ||
        PyModule_AddIntConstant(simulator, "FALLING", GPI_FALLING) < 0 ||
        PyModule_AddIntConstant(simulator, "VALUE_CHANGE", GPI_VALUE_CHANGE) <
            0 ||
        PyModule_AddIntConstant(simulator, "RANGE_UP", GPI_RANGE_UP) < 0 ||
        PyModule_AddIntConstant(simulator, "RANGE_DOWN", GPI_RANGE_DOWN) < 0 ||
        PyModule_AddIntConstant(simulator, "RANGE_NO_DIR", GPI_RANGE_NO_DIR) <
            0 ||
        PyModule_AddIntConstant(simulator, "LOGIC", GPI_LOGIC) < 0 ||
        PyModule_AddIntConstant(simulator, "LOGIC_ARRAY", GPI_LOGIC_ARRAY) <
            0 ||
        false) {
        return -1;
    }

    return 0;
}

// Add the extension types as entries in the module namespace
static int add_module_types(PyObject *simulator) {
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

    typ = (PyObject *)&gpi_hdl_Object<gpi_clk_hdl>::py_type;
    Py_INCREF(typ);
    if (PyModule_AddObject(simulator, "GpiClock", typ) < 0) {
        // LCOV_EXCL_START
        Py_DECREF(typ);
        return -1;
        // LCOV_EXCL_STOP
    }

    return 0;
}

/* NOTE: in the following docstrings we are specifying the parameters twice, but
 * this is necessary. The first docstring before the long '--' line specifies
 * the __text_signature__ that is used by the help() function. And the second
 * after the '--' line contains type annotations used by the
 * `autodoc_docstring_signature` setting of sphinx.ext.autodoc for generating
 * documentation because type annotations are not supported in
 * __text_signature__.
 */

static PyMethodDef SimulatorMethods[] = {
    {"get_root_handle", get_root_handle, METH_VARARGS,
     PyDoc_STR("get_root_handle(name, /)\n"
               "--\n\n"
               "get_root_handle(name: str) -> cocotb.simulator.gpi_sim_hdl\n"
               "Get the root handle.")},
    {"package_iterate", package_iterate, METH_NOARGS,
     PyDoc_STR("package_iterate(/)\n"
               "--\n\n"
               "package_iterate() -> cocotb.simulator.gpi_iterator_hdl\n"
               "Get an iterator handle to loop over all packages.\n"
               "\n"
               ".. versionadded:: 2.0")},
    {"register_timed_callback", register_timed_callback, METH_VARARGS,
     PyDoc_STR("register_timed_callback(time, func, /, *args)\n"
               "--\n\n"
               "register_timed_callback(time: int, func: Callable[..., Any], "
               "*args: Any) -> cocotb.simulator.gpi_cb_hdl\n"
               "Register a timed callback.")},
    {"register_value_change_callback", register_value_change_callback,
     METH_VARARGS,
     PyDoc_STR("register_value_change_callback(signal, func, edge, /, *args)\n"
               "--\n\n"
               "register_value_change_callback(signal: "
               "cocotb.simulator.gpi_sim_hdl, func: Callable[..., Any], edge: "
               "int, *args: Any) -> cocotb.simulator.gpi_cb_hdl\n"
               "Register a signal change callback.")},
    {"register_readonly_callback", register_readonly_callback, METH_VARARGS,
     PyDoc_STR("register_readonly_callback(func, /, *args)\n"
               "--\n\n"
               "register_readonly_callback(func: Callable[..., Any], *args: "
               "Any) -> cocotb.simulator.gpi_cb_hdl\n"
               "Register a callback for the read-only section.")},
    {"register_nextstep_callback", register_nextstep_callback, METH_VARARGS,
     PyDoc_STR("register_nextstep_callback(func, /, *args)\n"
               "--\n\n"
               "register_nextstep_callback(func: Callable[..., Any], *args: "
               "Any) -> cocotb.simulator.gpi_cb_hdl\n"
               "Register a callback for the cbNextSimTime callback.")},
    {"register_rwsynch_callback", register_rwsynch_callback, METH_VARARGS,
     PyDoc_STR("register_rwsynch_callback(func, /, *args)\n"
               "--\n\n"
               "register_rwsynch_callback(func: Callable[..., Any], *args: "
               "Any) -> cocotb.simulator.gpi_cb_hdl\n"
               "Register a callback for the read-write section.")},
    {"stop_simulator", stop_simulator, METH_VARARGS,
     PyDoc_STR("stop_simulator()\n"
               "--\n\n"
               "stop_simulator() -> None\n"
               "Instruct the attached simulator to stop. Users should not call "
               "this function.")},
    {"set_gpi_log_level", set_gpi_log_level, METH_VARARGS,
     PyDoc_STR("set_gpi_log_level(level, /)\n"
               "--\n\n"
               "set_gpi_log_level(level: int) -> None\n"
               "Set the log level of GPI logger.")},
    {"is_running", is_running, METH_NOARGS,
     PyDoc_STR("is_running()\n"
               "--\n\n"
               "is_running() -> bool\n"
               "Returns ``True`` if the caller is running within a simulator.\n"
               "\n"
               ".. versionadded:: 1.4")},
    {"get_sim_time", get_sim_time, METH_NOARGS,
     PyDoc_STR("get_sim_time()\n"
               "--\n\n"
               "get_sim_time() -> Tuple[int, int]\n"
               "Get the current simulation time.\n"
               "\n"
               "Time is represented as a tuple of 32 bit integers ([low32, "
               "high32]) comprising a single 64 bit integer.")},
    {"get_precision", get_precision, METH_NOARGS,
     PyDoc_STR("get_precision()\n"
               "--\n\n"
               "get_precision() -> int\n"
               "Get the precision of the simulator in powers of 10.\n"
               "\n"
               "For example, if ``-12`` is returned, the simulator's time "
               "precision is 10**-12 or 1 ps.")},
    {"get_simulator_product", get_simulator_product, METH_NOARGS,
     PyDoc_STR("get_simulator_product()\n"
               "--\n\n"
               "get_simulator_product() -> str\n"
               "Get the simulator's product string.")},
    {"get_simulator_version", get_simulator_version, METH_NOARGS,
     PyDoc_STR("get_simulator_version()\n"
               "--\n\n"
               "get_simulator_version() -> str\n"
               "Get the simulator's product version string.")},
    {"clock_create", clock_create, METH_VARARGS,
     PyDoc_STR("clock_create(signal, /)\n"
               "--\n\n"
               "clock_create(signal: cocotb.simulator.gpi_sim_hdl"
               ") -> cocotb.simulator.GpiClock\n"
               "Create a clock driver on a signal.\n"
               "\n"
               ".. versionadded:: 2.0")},
    {"initialize_logger", initialize_logger, METH_VARARGS,
     PyDoc_STR("initialize_logger(log_func, /)\n"
               "--\n\n"
               "initialize_logger("
               "log_func: Callable[[Logger, int, str, int, str, str], None], "
               "get_logger: Callable[[str], Logger]"
               ") -> None\n"
               "Initialize the GPI logger with Python logging functions.")},
    {"set_sim_event_callback", set_sim_event_callback, METH_VARARGS,
     PyDoc_STR("set_sim_event_callback(sim_event_callback, /)\n"
               "--\n\n"
               "set_sim_event_callback(sim_event_callback: Callable[[str], "
               "None]) -> None\n"
               "Set the callback for simulator events.")},
    {NULL, NULL, 0, NULL} /* Sentinel */
};

static struct PyModuleDef moduledef = {PyModuleDef_HEAD_INIT,
                                       MODULE_NAME,
                                       NULL,
                                       -1,
                                       SimulatorMethods,
                                       NULL,
                                       NULL,
                                       NULL,
                                       NULL};

#ifndef _WIN32
// Only required for Python < 3.9, default for 3.9+ (bpo-11410)
#pragma GCC visibility push(default)
PyMODINIT_FUNC PyInit_simulator(void);
#pragma GCC visibility pop
#endif

PyMODINIT_FUNC PyInit_simulator(void) {
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
    if (PyType_Ready(&gpi_hdl_Object<gpi_clk_hdl>::py_type) < 0) {
        // LCOV_EXCL_START
        return NULL;
        // LCOV_EXCL_STOP
    }

    PyObject *simulator = PyModule_Create(&moduledef);
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

/* NOTE: in the following docstrings we are specifying the parameters twice, but
 * this is necessary. The first docstring before the long '--' line specifies
 * the __text_signature__ that is used by the help() function. And the second
 * after the '--' line contains type annotations used by the
 * `autodoc_docstring_signature` setting of sphinx.ext.autodoc for generating
 * documentation because type annotations are not supported in
 * __text_signature__.
 */

static PyMethodDef gpi_sim_hdl_methods[] = {
    {"get_signal_val_long", (PyCFunction)get_signal_val_long, METH_NOARGS,
     PyDoc_STR("get_signal_val_long($self)\n"
               "--\n\n"
               "get_signal_val_long() -> int\n"
               "Get the value of a signal as an integer.")},
    {"get_signal_val_str", (PyCFunction)get_signal_val_str, METH_NOARGS,
     PyDoc_STR("get_signal_val_str($self)\n"
               "--\n\n"
               "get_signal_val_str() -> bytes\n"
               "Get the value of a signal as a byte string.")},
    {"get_signal_val_binstr", (PyCFunction)get_signal_val_binstr, METH_NOARGS,
     PyDoc_STR("get_signal_val_binstr($self)\n"
               "--\n\n"
               "get_signal_val_binstr() -> str\n"
               "Get the value of a logic vector signal as a string of (``0``, "
               "``1``, ``X``, etc.), one element per character.")},
    {"get_signal_val_real", (PyCFunction)get_signal_val_real, METH_NOARGS,
     PyDoc_STR("get_signal_val_real($self)\n"
               "--\n\n"
               "get_signal_val_real() -> float\n"
               "Get the value of a signal as a float.")},
    {"set_signal_val_int", (PyCFunction)set_signal_val_int, METH_VARARGS,
     PyDoc_STR("set_signal_val_int($self, action, value, /)\n"
               "--\n\n"
               "set_signal_val_int(action: int, value: int) -> None\n"
               "Set the value of a signal using an int.")},
    {"set_signal_val_str", (PyCFunction)set_signal_val_str, METH_VARARGS,
     PyDoc_STR("set_signal_val_str($self, action, value, /)\n"
               "--\n\n"
               "set_signal_val_str(action: int, value: bytes) -> None\n"
               "Set the value of a signal using a user-encoded string.")},
    {"set_signal_val_binstr", (PyCFunction)set_signal_val_binstr, METH_VARARGS,
     PyDoc_STR("set_signal_val_binstr($self, action, value, /)\n"
               "--\n\n"
               "set_signal_val_binstr(action: int, value: str) -> None\n"
               "Set the value of a logic vector signal using a string of "
               "(``0``, ``1``, ``X``, etc.), one element per character.")},
    {"set_signal_val_real", (PyCFunction)set_signal_val_real, METH_VARARGS,
     PyDoc_STR("set_signal_val_real($self, action, value, /)\n"
               "--\n\n"
               "set_signal_val_real(action: int, value: float) -> None\n"
               "Set the value of a signal using a float.")},
    {"get_definition_name", (PyCFunction)get_definition_name, METH_NOARGS,
     PyDoc_STR("get_definition_name($self)\n"
               "--\n\n"
               "get_definition_name() -> str\n"
               "Get the name of a GPI object's definition.")},
    {"get_definition_file", (PyCFunction)get_definition_file, METH_NOARGS,
     PyDoc_STR("get_definition_file($self)\n"
               "--\n\n"
               "get_definition_file() -> str\n"
               "Get the file that sources the object's definition.")},
    {"get_handle_by_name", (PyCFunction)get_handle_by_name, METH_VARARGS,
     PyDoc_STR("get_handle_by_name($self, name, discovery_method/)\n"
               "--\n\n"
               "get_handle_by_name(name: str, discovery_method: "
               "cocotb.handle._GPIDiscovery) -> "
               "cocotb.simulator.gpi_sim_hdl\n"
               "Get a handle to a child object by name.\n"
               "Specify discovery_method to determine the signal discovery "
               "strategy. AUTO by default.")},
    {"get_handle_by_index", (PyCFunction)get_handle_by_index, METH_VARARGS,
     PyDoc_STR(
         "get_handle_by_index($self, index, /)\n"
         "--\n\n"
         "get_handle_by_index(index: int) -> cocotb.simulator.gpi_sim_hdl\n"
         "Get a handle to a child object by index.")},
    {"get_name_string", (PyCFunction)get_name_string, METH_NOARGS,
     PyDoc_STR("get_name_string($self)\n"
               "--\n\n"
               "get_name_string() -> str\n"
               "Get the name of an object as a string.")},
    {"get_type_string", (PyCFunction)get_type_string, METH_NOARGS,
     PyDoc_STR("get_type_string($self)\n"
               "--\n\n"
               "get_type_string() -> str\n"
               "Get the GPI type of an object as a string.")},
    {"get_type", (PyCFunction)get_type, METH_NOARGS,
     PyDoc_STR("get_type($self)\n"
               "--\n\n"
               "get_type() -> int\n"
               "Get the GPI type of an object as an enum.")},
    {"get_const", (PyCFunction)get_const, METH_NOARGS,
     PyDoc_STR("get_const($self)\n"
               "--\n\n"
               "get_const() -> bool\n"
               "Return ``True`` if the object is a constant.")},
    {"get_num_elems", (PyCFunction)get_num_elems, METH_NOARGS,
     PyDoc_STR("get_num_elems($self)\n"
               "--\n\n"
               "get_num_elems() -> int\n"
               "Get the number of elements contained in the handle.")},
    {"get_range", (PyCFunction)get_range, METH_NOARGS,
     PyDoc_STR("get_range($self)\n"
               "--\n\n"
               "get_range() -> Tuple[int, int, int]\n"
               "Get the range of elements (tuple) contained in the handle. "
               "The first two elements of the tuple specify the left and right "
               "bounds, while the third specifies the direction (``1`` for "
               "ascending, ``-1`` for descending, and ``0`` for undefined).")},
    {"get_indexable", (PyCFunction)get_indexable, METH_NOARGS,
     PyDoc_STR("get_indexable($self)\n"
               "--\n\n"
               "get_indexable() -> bool\n"
               "Return ``True`` if indexable.")},
    {"iterate", (PyCFunction)iterate, METH_VARARGS,
     PyDoc_STR(
         "iterate($self, mode, /)\n"
         "--\n\n"
         "iterate(mode: int) -> cocotb.simulator.gpi_iterator_hdl\n"
         "Get an iterator handle to loop over all members in an object.")},
    {NULL, NULL, 0, NULL} /* Sentinel */
};

// putting these at the bottom means that all the functions above are accessible
template <>
PyTypeObject gpi_hdl_Object<gpi_sim_hdl>::py_type = []() -> PyTypeObject {
    auto type = fill_common_slots<gpi_sim_hdl>();
    type.tp_name = "cocotb.simulator.gpi_sim_hdl";
    type.tp_doc =
        "GPI object handle\n"
        "\n"
        "Contains methods for getting and setting the value of a GPI object, "
        "and introspection.";
    type.tp_methods = gpi_sim_hdl_methods;
    return type;
}();

template <>
PyTypeObject gpi_hdl_Object<gpi_iterator_hdl>::py_type = []() -> PyTypeObject {
    auto type = fill_common_slots<gpi_iterator_hdl>();
    type.tp_name = "cocotb.simulator.gpi_iterator_hdl";
    type.tp_doc = "GPI iterator handle.";
    type.tp_iter = PyObject_SelfIter;
    type.tp_iternext = (iternextfunc)next;
    return type;
}();

static PyMethodDef gpi_cb_hdl_methods[] = {
    {"deregister", (PyCFunction)deregister, METH_NOARGS,
     PyDoc_STR("deregister($self)\n"
               "--\n\n"
               "deregister() -> None\n"
               "De-register this callback.")},
    {NULL, NULL, 0, NULL} /* Sentinel */
};

template <>
PyTypeObject gpi_hdl_Object<gpi_cb_hdl>::py_type = []() -> PyTypeObject {
    auto type = fill_common_slots<gpi_cb_hdl>();
    type.tp_name = "cocotb.simulator.gpi_cb_hdl";
    type.tp_doc = "GPI callback handle";
    type.tp_methods = gpi_cb_hdl_methods;
    return type;
}();

static PyMethodDef gpi_clk_methods[] = {
    {"start", (PyCFunction)clk_start, METH_VARARGS,
     PyDoc_STR(
         "start($self, period_steps, high_steps, start_high)\n"
         "--\n\n"
         "start(period_steps: int, high_steps: int, start_high: bool) -> None\n"
         "Start this clock now.\n"
         "\n"
         "The clock will have a period of *period_steps* time steps, "
         "and out of that period it will be high for *high_steps* time steps. "
         "If *start_high* is ``True``, start at the beginning of the high "
         "state, "
         "otherwise start at the beginning of the low state.\n"
         "\n"
         "Raises:\n"
         "    TypeError: If there are an incorrect number of arguments or "
         "they are of the wrong type.\n"
         "    ValueError: If *period_steps* and *high_steps* are such that in "
         "one "
         "period the duration of the low or high state would be less "
         "than one time step, or *high_steps* is greater than *period_steps*.\n"
         "    RuntimeError: If the clock was already started, or the "
         "GPI callback could not be registered.")},
    {"stop", (PyCFunction)clk_stop, METH_NOARGS,
     PyDoc_STR("stop($self)\n"
               "--\n\n"
               "stop() -> None\n"
               "Stop this clock now.")},
    {NULL, NULL, 0, NULL} /* Sentinel */
};

template <>
PyTypeObject gpi_hdl_Object<gpi_clk_hdl>::py_type = []() -> PyTypeObject {
    auto type = fill_common_slots<gpi_clk_hdl>();
    type.tp_name = "cocotb.simulator.GpiClock";
    type.tp_doc = "C++ clock using the GPI.";
    type.tp_methods = gpi_clk_methods;
    type.tp_dealloc = clock_dealloc;
    return type;
}();
