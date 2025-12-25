// Copyright cocotb contributors
// Copyright (c) 2013 Potential Ventures Ltd
// Copyright (c) 2013 SolarFlare Communications Inc
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#ifndef COCOTB_GPI_LOGGING_H_
#define COCOTB_GPI_LOGGING_H_

/** @file gpi_logging.h

GPI Logging
===========

This header file defines how to produce logs for GPI implementations
as well as users of the GPI.
*/

#include <exports.h>
#include <gpi.h>

#include <cstdarg>  // va_list
#include <cstring>  // strlen

#ifdef GPI_EXPORTS
#define GPI_EXPORT COCOTB_EXPORT
#else
#define GPI_EXPORT COCOTB_IMPORT
#endif

extern GPI_EXPORT int gpi_debug_enabled;

/** @return The string representation of the GPI log level. */
GPI_EXPORT const char *gpi_log_level_to_str(enum gpi_log_level level);

/** Logs a message at a given log level using the current log handler.
 * The caller provides explicit location information.
 */
#define LOG_EXPLICIT(logger, level, file, func, lineno, ...) \
    gpi_log_(logger, level, file, func, lineno, __VA_ARGS__)

/** Logs a message at a given log level using the current log handler.
 * Automatically populates arguments using information in the called context.
 */
#define LOG_(level, ...) \
    gpi_log_("gpi", level, __FILE__, __func__, __LINE__, __VA_ARGS__)

/** Logs a message at TRACE log level using the current log handler.
 * Only logs if GPI debug is enabled.
 * Automatically populates arguments using information in the called context.
 */
#define LOG_TRACE(...)                    \
    do {                                  \
        if (gpi_debug_enabled) {          \
            LOG_(GPI_TRACE, __VA_ARGS__); \
        }                                 \
    } while (0)

/** Logs a message at DEBUG log level using the current log handler.
 * Automatically populates arguments using information in the called context.
 */
#define LOG_DEBUG(...) LOG_(GPI_DEBUG, __VA_ARGS__)

/** Logs a message at INFO log level using the current log handler.
 * Automatically populates arguments using information in the called context.
 */
#define LOG_INFO(...) LOG_(GPI_INFO, __VA_ARGS__)

/** Logs a message at WARN log level using the current log handler.
 * Automatically populates arguments using information in the called context.
 */
#define LOG_WARN(...) LOG_(GPI_WARNING, __VA_ARGS__)

/** Logs a message at ERROR log level using the current log handler.
 * Automatically populates arguments using information in the called context.
 */
#define LOG_ERROR(...) LOG_(GPI_ERROR, __VA_ARGS__)

/** Logs a message at CRITICAL log level using the current log handler.
 * Automatically populates arguments using information in the called context.
 */
#define LOG_CRITICAL(...) LOG_(GPI_CRITICAL, __VA_ARGS__)

#define MAKE_LOG_NAME_(extra_name) \
    (extra_name[0] == '\0' ? "gpi" : "gpi." extra_name)

/** Log a message using the currently registered log handler.
 *
 * @param extra_name  Name of the "gpi" child logger, "" for the root logger
 * @param level       Level at which to log the message
 * @param pathname    Name of the file where the call site is located
 * @param funcname    Name of the function where the call site is located
 * @param lineno      Line number of the call site
 * @param msg         The message to log, uses C-sprintf-style format specifier
 * @param ...         Additional arguments; formatted and inserted in message
 *                    according to format specifier in msg argument
 */
#define gpi_log(extra_name, level, pathname, funcname, lineno, ...)         \
    gpi_log_(MAKE_LOG_NAME_(extra_name), level, pathname, funcname, lineno, \
             __VA_ARGS__)

// Don't call this function directly unless the name is "gpi" or starts with
// "gpi."
GPI_EXPORT void gpi_log_(const char *name, enum gpi_log_level level,
                         const char *pathname, const char *funcname,
                         long lineno, const char *msg, ...);

/** Log a message using the currently registered log handler.
 *
 * @param extra_name  Name of the "gpi" child logger, "" for the root logger
 * @param level       Level at which to log the message
 * @param pathname    Name of the file where the call site is located
 * @param funcname    Name of the function where the call site is located
 * @param lineno      Line number of the call site
 * @param msg         The message to log, uses C-sprintf-style format specifier
 * @param args        Additional arguments; formatted and inserted in message
 *                    according to format specifier in msg argument
 */
#define gpi_vlog(extra_name, level, pathname, funcname, lineno, msg, args)   \
    gpi_vlog_(MAKE_LOG_NAME_(extra_name), level, pathname, funcname, lineno, \
              msg, args)

// Don't call this function directly unless the name is "gpi" or starts with
// "gpi."
GPI_EXPORT void gpi_vlog_(const char *name, enum gpi_log_level level,
                          const char *pathname, const char *funcname,
                          long lineno, const char *msg, va_list args);

#endif /* COCOTB_GPI_LOGGING_H_ */
