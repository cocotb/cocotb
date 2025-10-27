// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#ifndef PYGPI_PRIV_H_
#define PYGPI_PRIV_H_

#include <Python.h>
#include <gpi_logging.h>

void py_gpi_logger_initialize(PyObject *handler, PyObject *get_logger);

void py_gpi_logger_finalize();

extern PyObject *pEventFn;

extern int is_python_context;

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
