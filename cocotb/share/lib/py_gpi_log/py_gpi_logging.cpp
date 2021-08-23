// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include <Python.h>          // all things Python
#include <gpi_logging.h>     // all things GPI logging
#include <py_gpi_logging.h>  // PY_GPI_LOG_SIZE

#include <cstdarg>  // va_list, va_copy, va_end
#include <cstdio>   // fprintf, vsnprintf

static PyObject *pLogHandler = nullptr;

static PyObject *pLogFilter = nullptr;

static int py_gpi_log_level = GPIInfo;

static void py_gpi_log_handler(void *, const char *name, int level,
                               const char *pathname, const char *funcname,
                               long lineno, const char *msg, va_list argp) {
    if (level < py_gpi_log_level) {
        return;
    }

    va_list argp_copy;
    va_copy(argp_copy, argp);

    PyGILState_STATE gstate = PyGILState_Ensure();

    // Declared here in order to be initialized before any goto statements and
    // refcount cleanup
    PyObject *logger_name_arg = NULL, *filename_arg = NULL, *lineno_arg = NULL,
             *msg_arg = NULL, *function_arg = NULL;

    PyObject *level_arg = PyLong_FromLong(level);  // New reference
    if (level_arg == NULL) {
        // LCOV_EXCL_START
        goto error;
        // LCOV_EXCL_STOP
    }

    logger_name_arg = PyUnicode_FromString(name);  // New reference
    if (logger_name_arg == NULL) {
        // LCOV_EXCL_START
        goto error;
        // LCOV_EXCL_STOP
    }

    {
        // check if log level is enabled
        PyObject *filter_ret = PyObject_CallFunctionObjArgs(
            pLogFilter, logger_name_arg, level_arg, NULL);
        if (filter_ret == NULL) {
            // LCOV_EXCL_START
            goto error;
            // LCOV_EXCL_STOP
        }

        int is_enabled = PyObject_IsTrue(filter_ret);
        Py_DECREF(filter_ret);
        if (is_enabled < 0) {
            // LCOV_EXCL_START
            /* A Python exception occured while converting `filter_ret` to bool
             */
            goto error;
            // LCOV_EXCL_STOP
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
            // LCOV_EXCL_START
            fprintf(stderr, "Log message construction failed\n");
            // LCOV_EXCL_STOP
        }
    }

    filename_arg = PyUnicode_FromString(pathname);  // New reference
    if (filename_arg == NULL) {
        // LCOV_EXCL_START
        goto error;
        // LCOV_EXCL_STOP
    }

    lineno_arg = PyLong_FromLong(lineno);  // New reference
    if (lineno_arg == NULL) {
        // LCOV_EXCL_START
        goto error;
        // LCOV_EXCL_STOP
    }

    msg_arg = PyUnicode_FromString(log_buff);  // New reference
    if (msg_arg == NULL) {
        // LCOV_EXCL_START
        goto error;
        // LCOV_EXCL_STOP
    }

    function_arg = PyUnicode_FromString(funcname);  // New reference
    if (function_arg == NULL) {
        // LCOV_EXCL_START
        goto error;
        // LCOV_EXCL_STOP
    }

    {
        // Log function args are logger_name, level, filename, lineno, msg,
        // function
        PyObject *handler_ret = PyObject_CallFunctionObjArgs(
            pLogHandler, logger_name_arg, level_arg, filename_arg, lineno_arg,
            msg_arg, function_arg, NULL);
        if (handler_ret == NULL) {
            // LCOV_EXCL_START
            goto error;
            // LCOV_EXCL_STOP
        }
        Py_DECREF(handler_ret);
    }

    goto ok;
error:
    // LCOV_EXCL_START
    /* Note: don't call the LOG_ERROR macro because that might recurse */
    gpi_native_logger_vlog(name, level, pathname, funcname, lineno, msg,
                           argp_copy);
    gpi_native_logger_log("cocotb.gpi", GPIError, __FILE__, __func__, __LINE__,
                          "Error calling Python logging function from C++ "
                          "while logging the above");
    PyErr_Print();
    // LCOV_EXCL_STOP
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

extern "C" void py_gpi_logger_set_level(int level) {
    py_gpi_log_level = level;
    gpi_native_logger_set_level(level);
}

extern "C" void py_gpi_logger_initialize(PyObject *handler, PyObject *filter) {
    Py_INCREF(handler);
    Py_INCREF(filter);
    pLogHandler = handler;
    pLogFilter = filter;
    gpi_set_log_handler(py_gpi_log_handler, nullptr);
}

extern "C" void py_gpi_logger_finalize() {
    gpi_clear_log_handler();
    Py_XDECREF(pLogHandler);
    Py_XDECREF(pLogFilter);
}
