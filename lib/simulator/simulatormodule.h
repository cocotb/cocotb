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

#ifndef _SIMULATOR_MODULE_H
#define _SIMULATOR_MODULE_H

#include <Python.h>
#include "../compat/python3_compat.h"
#include "gpi_logging.h"
#include "gpi.h"

// This file defines the routines available to python

#define COCOTB_ACTIVE_ID        0xC0C07B        // User data flag to indicate callback is active
#define COCOTB_INACTIVE_ID      0xDEADB175      // User data flag set when callback has been deregistered

#define MODULE_NAME "simulator"

// callback user data
typedef struct t_callback_data {
    PyThreadState *_saved_thread_state; // Thread state of the calling thread FIXME is this required?
    uint32_t id_value;                  // COCOTB_ACTIVE_ID or COCOTB_INACTIVE_ID
    PyObject *function;                 // Fuction to call when the callback fires
    PyObject *args;                     // The arguments to call the function with
    PyObject *kwargs;                   // Keyword arguments to call the function with
    gpi_sim_hdl cb_hdl;
} s_callback_data, *p_callback_data;

static PyObject *error_out(PyObject *m);
static PyObject *log_msg(PyObject *self, PyObject *args);

// Raise an exception on failure
// Return None if for example get bin_string on enum?
static PyObject *get_signal_val_long(PyObject *self, PyObject *args);
static PyObject *get_signal_val_real(PyObject *self, PyObject *args);
static PyObject *get_signal_val_str(PyObject *self, PyObject *args);
static PyObject *get_signal_val_binstr(PyObject *self, PyObject *args);
static PyObject *set_signal_val_long(PyObject *self, PyObject *args);
static PyObject *set_signal_val_real(PyObject *self, PyObject *args);
static PyObject *set_signal_val_str(PyObject *self, PyObject *args);
static PyObject *get_definition_name(PyObject *self, PyObject *args);
static PyObject *get_definition_file(PyObject *self, PyObject *args);
static PyObject *get_handle_by_name(PyObject *self, PyObject *args);
static PyObject *get_handle_by_index(PyObject *self, PyObject *args);
static PyObject *get_root_handle(PyObject *self, PyObject *args);
static PyObject *get_name_string(PyObject *self, PyObject *args);
static PyObject *get_type(PyObject *self, PyObject *args);
static PyObject *get_const(PyObject *self, PyObject *args);
static PyObject *get_type_string(PyObject *self, PyObject *args);
static PyObject *get_num_elems(PyObject *self, PyObject *args);
static PyObject *get_range(PyObject *self, PyObject *args);
static PyObject *register_timed_callback(PyObject *self, PyObject *args);
static PyObject *register_value_change_callback(PyObject *self, PyObject *args);
static PyObject *register_readonly_callback(PyObject *self, PyObject *args);
static PyObject *register_nextstep_callback(PyObject *self, PyObject *args);
static PyObject *register_rwsynch_callback(PyObject *self, PyObject *args);
static PyObject *stop_simulator(PyObject *self, PyObject *args);

static PyObject *iterate(PyObject *self, PyObject *args);
static PyObject *next(PyObject *self, PyObject *args);

static PyObject *get_sim_time(PyObject *self, PyObject *args);
static PyObject *get_precision(PyObject *self, PyObject *args);
static PyObject *deregister_callback(PyObject *self, PyObject *args);

static PyObject *log_level(PyObject *self, PyObject *args);

static PyMethodDef SimulatorMethods[] = {
    {"log_msg",         log_msg, METH_VARARGS, "Log a message"},
    {"get_signal_val_long", get_signal_val_long, METH_VARARGS, "Get the value of a signal as a long"},
    {"get_signal_val_str", get_signal_val_str, METH_VARARGS, "Get the value of a signal as an ascii string"},
    {"get_signal_val_binstr", get_signal_val_binstr, METH_VARARGS, "Get the value of a signal as a binary string"},
    {"get_signal_val_real", get_signal_val_real, METH_VARARGS, "Get the value of a signal as a double precision float"},
    {"set_signal_val_long", set_signal_val_long, METH_VARARGS, "Set the value of a signal using a long"},
    {"set_signal_val_str", set_signal_val_str, METH_VARARGS, "Set the value of a signal using a binary string"},
    {"set_signal_val_real", set_signal_val_real, METH_VARARGS, "Set the value of a signal using a double precision float"},
    {"get_definition_name", get_definition_name, METH_VARARGS, "Get the name of a GPI object's definition"},
    {"get_definition_file", get_definition_file, METH_VARARGS, "Get the file that sources the object's definition"},
    {"get_handle_by_name", get_handle_by_name, METH_VARARGS, "Get handle of a named object"},
    {"get_handle_by_index", get_handle_by_index, METH_VARARGS, "Get handle of a object at an index in a parent"},
    {"get_root_handle", get_root_handle, METH_VARARGS, "Get the root handle"},
    {"get_name_string", get_name_string, METH_VARARGS, "Get the name of an object as a string"},
    {"get_type_string", get_type_string, METH_VARARGS, "Get the type of an object as a string"},
    {"get_type", get_type, METH_VARARGS, "Get the type of an object, mapped to a GPI enumeration"},
    {"get_const", get_const, METH_VARARGS, "Get a flag indicating whether the object is a constant"},
    {"get_num_elems", get_num_elems, METH_VARARGS, "Get the number of elements contained in the handle"},
    {"get_range", get_range, METH_VARARGS, "Get the range of elements (tuple) contained in the handle, Returns None if not indexable"},
    {"register_timed_callback", register_timed_callback, METH_VARARGS, "Register a timed callback"},
    {"register_value_change_callback", register_value_change_callback, METH_VARARGS, "Register a signal change callback"},
    {"register_readonly_callback", register_readonly_callback, METH_VARARGS, "Register a callback for readonly section"},
    {"register_nextstep_callback", register_nextstep_callback, METH_VARARGS, "Register a cllback for the nextsimtime callback"},
    {"register_rwsynch_callback", register_rwsynch_callback, METH_VARARGS, "Register a callback for the readwrite section"},
    {"stop_simulator", stop_simulator, METH_VARARGS, "Instruct the attached simulator to stop"},
    {"iterate", iterate, METH_VARARGS, "Get an iterator handle to loop over all members in an object"},
    {"next", next, METH_VARARGS, "Get the next object from the iterator"},
    {"log_level", log_level, METH_VARARGS, "Set the log level for GPI"},

    // FIXME METH_NOARGS => initialization from incompatible pointer type
    {"get_sim_time", get_sim_time, METH_VARARGS, "Get the current simulation time as an int tuple"},
    {"get_precision", get_precision, METH_VARARGS, "Get the precision of the simualator"},
    {"deregister_callback", deregister_callback, METH_VARARGS, "Deregister a callback"},
    
    {"error_out", (PyCFunction)error_out, METH_NOARGS, NULL},
    
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

#endif
