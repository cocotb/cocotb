// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#ifndef PY_GPI_LOGGING_H
#define PY_GPI_LOGGING_H

#include <Python.h>

#include "exports.h"
#include "gpi_logging.h"

#ifdef PYGPILOG_EXPORTS
#define PYGPILOG_EXPORT COCOTB_EXPORT
#else
#define PYGPILOG_EXPORT COCOTB_IMPORT
#endif

PYGPILOG_EXPORT void py_gpi_logger_set_level(int level);

PYGPILOG_EXPORT void py_gpi_logger_initialize(PyObject* handler,
                                              PyObject* get_logger);

PYGPILOG_EXPORT void py_gpi_logger_finalize();

// The following stuff has nothing to do with logging, but this module is shared
// between the other two PyGPI modules: simulatormodule.so and libcocotb.so.

extern PYGPILOG_EXPORT PyObject* pEventFn;

extern PYGPILOG_EXPORT int is_python_context;

// to_python and to_simulator are implemented as macros instead of functions so
// that the logs reference the user's lineno and filename

#define to_python()                                      \
    do {                                                 \
        if (is_python_context) {                         \
            LOG_ERROR("FATAL: We are calling up again"); \
            exit(1);                                     \
        }                                                \
        ++is_python_context;                             \
        LOG_TRACE("Returning to Python");                \
    } while (0)

#define to_simulator()                                              \
    do {                                                            \
        if (!is_python_context) {                                   \
            LOG_ERROR("FATAL: We have returned twice from Python"); \
            exit(1);                                                \
        }                                                           \
        --is_python_context;                                        \
        LOG_TRACE("Returning to simulator");                        \
    } while (0)

#endif
