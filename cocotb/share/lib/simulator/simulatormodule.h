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
static PyObject *is_running(PyObject *self, PyObject *args);
static PyObject *get_sim_time(PyObject *self, PyObject *args);
static PyObject *get_precision(PyObject *self, PyObject *args);
static PyObject *get_simulator_product(PyObject *self, PyObject *args);
static PyObject *get_simulator_version(PyObject *self, PyObject *args);

static PyObject *log_level(PyObject *self, PyObject *args);

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
        "Register a callback for the NextSimTime callback."
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

#endif
