// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include <Python.h>          // all things Python
#include <cocotb_utils.h>    // DEFER
#include <gpi_logging.h>     // all things GPI logging
#include <py_gpi_logging.h>  // this library

#include <cstdarg>  // va_list, va_copy, va_end
#include <cstdio>   // fprintf, vsnprintf
#include <vector>   // std::vector

static PyObject *pLogHandler = nullptr;

static PyObject *pLogFilter = nullptr;

static int py_gpi_log_level = GPIInfo;

static void fallback_handler(const char *name, int level, const char *pathname,
                             const char *funcname, long lineno,
                             const char *msg) {
    // Note: don't call the LOG_ERROR macro because that might recurse
    gpi_native_logger_log(name, level, pathname, funcname, lineno, msg);
    gpi_native_logger_log("gpi", GPIError, __FILE__, __func__, __LINE__,
                          "Error calling Python logging function from C++ "
                          "while logging the above");
}

static void py_gpi_log_handler(void *, const char *name, int level,
                               const char *pathname, const char *funcname,
                               long lineno, const char *msg, va_list argp) {
    if (level < py_gpi_log_level) {
        return;
    }

    va_list argp_copy;
    va_copy(argp_copy, argp);
    DEFER(va_end(argp_copy));

    // before the log buffer to ensure it isn't clobbered.
    PyGILState_STATE gstate = PyGILState_Ensure();
    DEFER(PyGILState_Release(gstate));

    static std::vector<char> log_buff(512);

    log_buff.clear();
    int n = vsnprintf(log_buff.data(), log_buff.capacity(), msg, argp);
    if (n < 0) {
        // On Windows with the Visual C Runtime prior to 2015 the above call to
        // vsnprintf will return -1 if the buffer would overflow, rather than
        // the number of bytes that would be written as required by the C99
        // standard.
        // https://docs.microsoft.com/en-us/cpp/c-runtime-library/reference/vsnprintf-vsnprintf-vsnprintf-l-vsnwprintf-vsnwprintf-l
        // So we try the call again with the buffer NULL and the size 0, which
        // should return the number of bytes that would be written.
        va_list argp_copy_again;
        va_copy(argp_copy_again, argp_copy);
        DEFER(va_end(argp_copy_again));
        n = vsnprintf(NULL, 0, msg, argp_copy_again);
        if (n < 0) {
            // Here we know the error is for real, so we complain and move on.
            // LCOV_EXCL_START
            fprintf(stderr,
                    "Log message construction failed: (error code) %d\n", n);
            return;
            // LCOV_EXCL_STOP
        }
    }
    if ((unsigned)n >= log_buff.capacity()) {
        log_buff.reserve((unsigned)n + 1);
        n = vsnprintf(log_buff.data(), (unsigned)n + 1, msg, argp_copy);
        if (n < 0) {
            // LCOV_EXCL_START
            fprintf(stderr,
                    "Log message construction failed: (error code) %d\n", n);
            return;
            // LCOV_EXCL_STOP
        }
    }

    PyObject *level_arg = PyLong_FromLong(level);  // New reference
    if (level_arg == NULL) {
        // LCOV_EXCL_START
        PyErr_Print();
        return fallback_handler(name, level, pathname, funcname, lineno,
                                log_buff.data());
        // LCOV_EXCL_STOP
    }
    DEFER(Py_DECREF(level_arg));

    PyObject *logger_name_arg = PyUnicode_FromString(name);  // New reference
    if (logger_name_arg == NULL) {
        // LCOV_EXCL_START
        PyErr_Print();
        return fallback_handler(name, level, pathname, funcname, lineno,
                                log_buff.data());
        // LCOV_EXCL_STOP
    }
    DEFER(Py_DECREF(logger_name_arg));

    // check if log level is enabled
    PyObject *filter_ret = PyObject_CallFunctionObjArgs(
        pLogFilter, logger_name_arg, level_arg, NULL);
    if (filter_ret == NULL) {
        // LCOV_EXCL_START
        PyErr_Print();
        return fallback_handler(name, level, pathname, funcname, lineno,
                                log_buff.data());
        // LCOV_EXCL_STOP
    }

    int is_enabled = PyObject_IsTrue(filter_ret);
    Py_DECREF(filter_ret);
    if (is_enabled < 0) {
        // LCOV_EXCL_START
        PyErr_Print();
        return fallback_handler(name, level, pathname, funcname, lineno,
                                log_buff.data());
        // LCOV_EXCL_STOP
    }

    if (!is_enabled) {
        return;
    }

    PyObject *filename_arg = PyUnicode_FromString(pathname);  // New reference
    if (filename_arg == NULL) {
        // LCOV_EXCL_START
        PyErr_Print();
        return fallback_handler(name, level, pathname, funcname, lineno,
                                log_buff.data());
        // LCOV_EXCL_STOP
    }
    DEFER(Py_DECREF(filename_arg));

    PyObject *lineno_arg = PyLong_FromLong(lineno);  // New reference
    if (lineno_arg == NULL) {
        // LCOV_EXCL_START
        PyErr_Print();
        return fallback_handler(name, level, pathname, funcname, lineno,
                                log_buff.data());
        // LCOV_EXCL_STOP
    }
    DEFER(Py_DECREF(lineno_arg));

    PyObject *msg_arg = PyUnicode_FromString(log_buff.data());  // New reference
    if (msg_arg == NULL) {
        // LCOV_EXCL_START
        PyErr_Print();
        return fallback_handler(name, level, pathname, funcname, lineno,
                                log_buff.data());
        // LCOV_EXCL_STOP
    }
    DEFER(Py_DECREF(msg_arg));

    PyObject *function_arg = PyUnicode_FromString(funcname);  // New reference
    if (function_arg == NULL) {
        // LCOV_EXCL_START
        PyErr_Print();
        return fallback_handler(name, level, pathname, funcname, lineno,
                                log_buff.data());
        // LCOV_EXCL_STOP
    }
    DEFER(Py_DECREF(function_arg))

    // Log function args are logger_name, level, filename, lineno, msg, function
    PyObject *handler_ret = PyObject_CallFunctionObjArgs(
        pLogHandler, logger_name_arg, level_arg, filename_arg, lineno_arg,
        msg_arg, function_arg, NULL);
    if (handler_ret == NULL) {
        // LCOV_EXCL_START
        PyErr_Print();
        return fallback_handler(name, level, pathname, funcname, lineno,
                                log_buff.data());
        // LCOV_EXCL_STOP
    }
    Py_DECREF(handler_ret);
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
