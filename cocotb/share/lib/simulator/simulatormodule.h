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
#include "gpi_logging.h"
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

static PyObject *log_msg(PyObject *self, PyObject *args);

static PyObject *register_timed_callback(PyObject *self, PyObject *args);
static PyObject *register_value_change_callback(PyObject *self, PyObject *args);
static PyObject *register_readonly_callback(PyObject *self, PyObject *args);
static PyObject *register_nextstep_callback(PyObject *self, PyObject *args);
static PyObject *register_rwsynch_callback(PyObject *self, PyObject *args);

static PyObject *get_root_handle(PyObject *self, PyObject *args);
static PyObject *stop_simulator(PyObject *self, PyObject *args);

static PyObject *get_sim_time(PyObject *self, PyObject *args);
static PyObject *get_precision(PyObject *self, PyObject *args);
static PyObject *get_simulator_product(PyObject *self, PyObject *args);
static PyObject *get_simulator_version(PyObject *self, PyObject *args);

static PyObject *log_level(PyObject *self, PyObject *args);

static PyMethodDef SimulatorMethods[] = {
    {"log_msg", log_msg, METH_VARARGS, PyDoc_STR(
        "log_msg(name, path, funcname, lineno, msg, /)\n"
        "--\n\n"
        "Log a message"
    )},
    {"get_root_handle", get_root_handle, METH_VARARGS, PyDoc_STR(
        "get_root_handle(name, /)\n"
        "--\n\n"
        "Get the root handle"
    )},
    {"register_timed_callback", register_timed_callback, METH_VARARGS, PyDoc_STR(
        "register_timed_callback(time, func, /, *args)\n"
        "--\n\n"
        "Register a timed callback"
    )},
    {"register_value_change_callback", register_value_change_callback, METH_VARARGS, PyDoc_STR(
        "register_value_change_callback(signal, func, edge, /, *args)\n"
        "--\n\n"
        "Register a signal change callback"
    )},
    {"register_readonly_callback", register_readonly_callback, METH_VARARGS, PyDoc_STR(
        "register_readonly_callback(func, /, *args)\n"
        "--\n\n"
        "Register a callback for the read-only section"
    )},
    {"register_nextstep_callback", register_nextstep_callback, METH_VARARGS, PyDoc_STR(
        "register_nextstep_callback(func, /, *args)\n"
        "--\n\n"
        "Register a callback for the NextSimTime callback"
    )},
    {"register_rwsynch_callback", register_rwsynch_callback, METH_VARARGS, PyDoc_STR(
        "register_rwsynch_callback(func, /, *args)\n"
        "--\n\n"
        "Register a callback for the read-write section"
    )},
    {"stop_simulator", stop_simulator, METH_VARARGS, PyDoc_STR(
        "stop_simulator()\n"
        "--\n\n"
        "Instruct the attached simulator to stop"
    )},
    {"log_level", log_level, METH_VARARGS, PyDoc_STR(
        "log_level(level, /)\n"
        "--\n\n"
        "Set the log level for GPI"
    )},

    {"get_sim_time", get_sim_time, METH_NOARGS, PyDoc_STR(
        "get_sim_time()\n"
        "--\n\n"
        "Get the current simulation time as an int tuple"
    )},
    {"get_precision", get_precision, METH_NOARGS, PyDoc_STR(
        "get_precision()\n"
        "--\n\n"
        "Get the precision of the simulator"
    )},
    {"get_simulator_product", get_simulator_product, METH_NOARGS, PyDoc_STR(
        "get_simulator_product()\n"
        "--\n\n"
        "Simulator product information"
    )},
    {"get_simulator_version", get_simulator_version, METH_NOARGS, PyDoc_STR(
        "get_simulator_version()\n"
        "--\n\n"
        "Simulator product version information"
    )},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

#endif
