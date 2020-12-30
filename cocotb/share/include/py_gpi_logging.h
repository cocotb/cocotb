// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#ifndef PY_GPI_LOGGING_H
#define PY_GPI_LOGGING_H

#include <exports.h>
#ifdef PYGPILOG_EXPORTS
#define PYGPILOG_EXPORT COCOTB_EXPORT
#else
#define PYGPILOG_EXPORT COCOTB_IMPORT
#endif

#define PY_GPI_LOG_SIZE 1024

#ifdef __cplusplus
extern "C" {
#endif

PYGPILOG_EXPORT void py_gpi_logger_set_level(int level);

PYGPILOG_EXPORT void py_gpi_logger_initialize(PyObject * handler, PyObject * filter);

PYGPILOG_EXPORT void py_gpi_logger_finalize();

extern PYGPILOG_EXPORT int is_python_context;

// to_python and to_simulator are implemented as macros instead of functions so
// that the logs reference the user's lineno and filename

#define to_python() do { \
    if (is_python_context) { \
        LOG_ERROR("FATAL: We are calling up again"); \
        exit(1); \
    } \
    ++is_python_context; \
    LOG_DEBUG("Returning to Python"); \
} while (0)

#define to_simulator() do { \
    if (!is_python_context) { \
        LOG_ERROR("FATAL: We have returned twice from Python"); \
        exit(1); \
    } \
    --is_python_context; \
    LOG_DEBUG("Returning to simulator"); \
} while (0)

#ifdef __cplusplus
}
#endif

#endif
