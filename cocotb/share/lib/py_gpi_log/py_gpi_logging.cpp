// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include <Python.h>         // all things Python
#include <gpi_logging.h>    // all things GPI logging
#include <py_gpi_logging.h> // PY_GPI_LOG_SIZE
#include <cstdarg>          // va_list, va_copy, va_end
#include <cstdio>           // fprintf, vsnprintf


static PyObject *pLogHandler = nullptr;

static PyObject *pLogFilter = nullptr;

static int py_gpi_log_level = GPIInfo;


/**
 * @name    GPI logging
 * @brief   Write a log message using cocotb SimLog class
 * @ingroup python_c_api
 *
 * GILState before calling: Unknown
 *
 * GILState after calling: Unknown
 *
 * Makes one call to PyGILState_Ensure and one call to PyGILState_Release
 *
 * If the Python logging mechanism is not initialised, dumps to `stderr`.
 *
 */
static void py_gpi_log_handler(
    void *userdata,
    const char *name,
    int level,
    const char *pathname,
    const char *funcname,
    long lineno,
    const char *msg,
    va_list argp)
{
    (void)userdata;

    if (!pLogHandler) {
        gpi_native_logger_vlog(name, level, pathname, funcname, lineno, msg, argp);
        return;
    }

    if (level < py_gpi_log_level) {
        return;
    }

    va_list argp_copy;
    va_copy(argp_copy, argp);

    PyGILState_STATE gstate = PyGILState_Ensure();

    // Declared here in order to be initialized before any goto statements and refcount cleanup
    PyObject *logger_name_arg = NULL, *filename_arg = NULL, *lineno_arg = NULL, *msg_arg = NULL, *function_arg = NULL;

    PyObject *level_arg = PyLong_FromLong(level);                  // New reference
    if (level_arg == NULL) {
        goto error;
    }

    logger_name_arg = PyUnicode_FromString(name);      // New reference
    if (logger_name_arg == NULL) {
        goto error;
    }

    {
        // check if log level is enabled
        PyObject *filter_ret = PyObject_CallFunctionObjArgs(pLogFilter, logger_name_arg, level_arg, NULL);
        if (filter_ret == NULL) {
            goto error;
        }

        int is_enabled = PyObject_IsTrue(filter_ret);
        Py_DECREF(filter_ret);
        if (is_enabled < 0) {
            /* A python exception occured while converting `filter_ret` to bool */
            goto error;
        }

        if (!is_enabled) {
            goto ok;
        }
    }

    static char log_buff[PY_GPI_LOG_SIZE];

    // Ignore truncation
    {
        int n = vsnprintf(log_buff, sizeof(log_buff), msg, argp);
        if (n < 0 || n >= (int)sizeof(log_buff)) {
            fprintf(stderr, "Log message construction failed\n");
        }
    }

    filename_arg = PyUnicode_FromString(pathname);      // New reference
    if (filename_arg == NULL) {
        goto error;
    }

    lineno_arg = PyLong_FromLong(lineno);               // New reference
    if (lineno_arg == NULL) {
        goto error;
    }

    msg_arg = PyUnicode_FromString(log_buff);           // New reference
    if (msg_arg == NULL) {
        goto error;
    }

    function_arg = PyUnicode_FromString(funcname);      // New reference
    if (function_arg == NULL) {
        goto error;
    }

    {
        // Log function args are logger_name, level, filename, lineno, msg, function
        PyObject *handler_ret = PyObject_CallFunctionObjArgs(pLogHandler, logger_name_arg, level_arg, filename_arg, lineno_arg, msg_arg, function_arg, NULL);
        if (handler_ret == NULL) {
            goto error;
        }
        Py_DECREF(handler_ret);
    }

    goto ok;
error:
    /* Note: don't call the LOG_ERROR macro because that might recurse */
    gpi_native_logger_vlog(name, level, pathname, funcname, lineno, msg, argp_copy);
    gpi_native_logger_log("cocotb.gpi", GPIError, __FILE__, __func__, __LINE__, "Error calling Python logging function from C while logging the above");
    PyErr_Print();
ok:
    va_end(argp_copy);
    Py_XDECREF(logger_name_arg);
    Py_XDECREF(level_arg);
    Py_XDECREF(filename_arg);
    Py_XDECREF(lineno_arg);
    Py_XDECREF(msg_arg);
    Py_XDECREF(function_arg);
    PyGILState_Release(gstate);
}


extern "C" void py_gpi_set_log_level(int level)
{
    py_gpi_log_level = level;
}


extern "C" void py_gpi_initialize(PyObject * handler, PyObject * filter)
{
    pLogHandler = handler;
    pLogFilter = filter;
    gpi_set_log_handler(py_gpi_log_handler, nullptr);
}


extern "C" void py_gpi_finalize()
{
    gpi_clear_log_handler();
    Py_XDECREF(pLogHandler);
    Py_XDECREF(pLogFilter);
}
