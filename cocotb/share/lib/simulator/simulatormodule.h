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
typedef struct t_callback_data {
    PyThreadState *_saved_thread_state; // Thread state of the calling thread FIXME is this required?
    uint32_t id_value;                  // COCOTB_ACTIVE_ID or COCOTB_INACTIVE_ID
    PyObject *function;                 // Function to call when the callback fires
    PyObject *args;                     // The arguments to call the function with
    PyObject *kwargs;                   // Keyword arguments to call the function with
    gpi_sim_hdl cb_hdl;
} s_callback_data, *p_callback_data;

static PyObject *error_out(PyObject *m, PyObject *args);
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

static PyObject *log_level(PyObject *self, PyObject *args);

static PyMethodDef SimulatorMethods[] = {
    {"log_msg", log_msg, METH_VARARGS, "Log a message"},
    {"get_root_handle", get_root_handle, METH_VARARGS, "Get the root handle"},
    {"register_timed_callback", register_timed_callback, METH_VARARGS, "Register a timed callback"},
    {"register_value_change_callback", register_value_change_callback, METH_VARARGS, "Register a signal change callback"},
    {"register_readonly_callback", register_readonly_callback, METH_VARARGS, "Register a callback for the read-only section"},
    {"register_nextstep_callback", register_nextstep_callback, METH_VARARGS, "Register a callback for the NextSimTime callback"},
    {"register_rwsynch_callback", register_rwsynch_callback, METH_VARARGS, "Register a callback for the read-write section"},
    {"stop_simulator", stop_simulator, METH_VARARGS, "Instruct the attached simulator to stop"},
    {"log_level", log_level, METH_VARARGS, "Set the log level for GPI"},

    {"get_sim_time", get_sim_time, METH_NOARGS, "Get the current simulation time as an int tuple"},
    {"get_precision", get_precision, METH_NOARGS, "Get the precision of the simulator"},
    {"error_out", error_out, METH_NOARGS, NULL},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

#endif
