// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#ifndef PY_GPI_LOGGING_H
#define PY_GPI_LOGGING_H

#include <Python.h>
#include <gpi_logging.h>

#ifdef PYGPI_EXPORTS
#define PYGPI_EXPORT COCOTB_EXPORT
#else
#define PYGPI_EXPORT COCOTB_IMPORT
#endif

void py_gpi_logger_initialize(PyObject *handler, PyObject *get_logger);
void py_gpi_logger_finalize();
void py_gpi_log_set_level(int level);

extern PyObject *pEventFn;
extern int pygpi_debug_enabled;
extern int python_context_tracing_enabled;
extern int is_python_context;

#define PYGPI_LOG_(level, ...) \
    gpi_log_("pygpi", level, __FILE__, __func__, __LINE__, __VA_ARGS__)

/** Logs a message at TRACE log level if PYGPI tracing is enabled */
#define PYGPI_LOG_TRACE(...)                    \
    do {                                        \
        if (pygpi_debug_enabled) {              \
            PYGPI_LOG_(GPI_TRACE, __VA_ARGS__); \
        }                                       \
    } while (0)

/** Logs a message at DEBUG log level using the current log handler.
 * Automatically populates arguments using information in the called context.
 */
#define PYGPI_LOG_DEBUG(...) PYGPI_LOG_(GPI_DEBUG, __VA_ARGS__)

/** Logs a message at INFO log level using the current log handler.
 * Automatically populates arguments using information in the called context.
 */
#define PYGPI_LOG_INFO(...) PYGPI_LOG_(GPI_INFO, __VA_ARGS__)

/** Logs a message at WARN log level using the current log handler.
 * Automatically populates arguments using information in the called context.
 */
#define PYGPI_LOG_WARN(...) PYGPI_LOG_(GPI_WARNING, __VA_ARGS__)

/** Logs a message at ERROR log level using the current log handler.
 * Automatically populates arguments using information in the called context.
 */
#define PYGPI_LOG_ERROR(...) PYGPI_LOG_(GPI_ERROR, __VA_ARGS__)

/** Logs a message at CRITICAL log level using the current log handler.
 * Automatically populates arguments using information in the called context.
 */
#define PYGPI_LOG_CRITICAL(...) PYGPI_LOG_(GPI_CRITICAL, __VA_ARGS__)

// c_to_python and python_to_c are implemented as macros instead of functions so
// that the logs reference the user's lineno and filename

#define c_to_python()                                                  \
    do {                                                               \
        if (python_context_tracing_enabled) {                          \
            if (is_python_context) {                                   \
                PYGPI_LOG_CRITICAL(                                    \
                    "FATAL: Trying C => Python but already in Python " \
                    "context");                                        \
                exit(1);                                               \
            }                                                          \
            ++is_python_context;                                       \
            PYGPI_LOG_TRACE("C => Python");                            \
        }                                                              \
    } while (0)

#define python_to_c()                                                      \
    do {                                                                   \
        if (python_context_tracing_enabled) {                              \
            if (!is_python_context) {                                      \
                PYGPI_LOG_CRITICAL(                                        \
                    "FATAL: Trying Python => C but already in C context"); \
                exit(1);                                                   \
            }                                                              \
            --is_python_context;                                           \
            PYGPI_LOG_TRACE("Python => C");                                \
        }                                                                  \
    } while (0)

#endif
