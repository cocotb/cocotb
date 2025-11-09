// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#ifndef PY_GPI_LOGGING_H
#define PY_GPI_LOGGING_H

#include <Python.h>

#include "exports.h"

#ifdef PYGPILOG_EXPORTS
#define PYGPILOG_EXPORT COCOTB_EXPORT
#else
#define PYGPILOG_EXPORT COCOTB_IMPORT
#endif

#include <gpi_logging.h>

#ifdef __cplusplus
extern "C" {
#endif

PYGPILOG_EXPORT void py_gpi_logger_initialize(PyObject *handler,
                                              PyObject *get_logger);

PYGPILOG_EXPORT void py_gpi_logger_finalize();

extern PYGPILOG_EXPORT PyObject *pEventFn;  // This is gross but I don't care

extern "C" PYGPILOG_EXPORT int pygpi_debug_enabled;

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

#ifdef __cplusplus
}
#endif

#endif
