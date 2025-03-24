// Copyright cocotb contributors
// Copyright (c) 2013 Potential Ventures Ltd
// Copyright (c) 2013 SolarFlare Communications Inc
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#ifndef COCOTB_GPI_LOGGING_H_
#define COCOTB_GPI_LOGGING_H_

#include <cstdarg>  // va_list
#include <cstring>  // strlen

#include "exports.h"

#ifdef GPILOG_EXPORTS
#define GPILOG_EXPORT COCOTB_EXPORT
#else
#define GPILOG_EXPORT COCOTB_IMPORT
#endif

#ifdef __cplusplus
extern "C" {
#endif

/** Named logging level
 *
 *  The native logger only logs level names at these log level values.
 *  They were specifically chosen to align with the default level values in the
 *  Python logging module. Implementers of custom loggers should emit human
 *  readable level names for these value, but may support other values.
 */
enum gpi_log_level {
    GPI_NOTSET = 0,  ///< Lets the parent logger in the hierarchy decide the
                     ///< effective log level. By default this behaves like
                     ///< `INFO`.
    GPI_TRACE = 5,   ///< Prints `TRACE` by default. Information about execution
                     ///< of simulator callbacks and Python/simulator contexts.
    GPI_DEBUG = 10,  ///< Prints `DEBUG` by default. Verbose information, useful
                     ///< for debugging.
    GPI_INFO = 20,   ///< Prints `INFO` by default. Information about major
                     ///< events in the current program.
    GPI_WARNING = 30,  ///< Prints `WARN` by default. Encountered a recoverable
                       ///< bug, or information about surprising behavior.
    GPI_ERROR = 40,    ///< Prints `ERROR` by default. An unrecoverable error
    GPI_CRITICAL = 50  ///< Prints `CRITICAL` by default. An unrecoverable
                       ///< error, to be followed by immediate simulator
                       ///< shutdown.
};

#define LOG_EXPLICIT(logger, level, file, func, lineno, ...) \
    gpi_log_(logger, level, file, func, lineno, __VA_ARGS__)

#define LOG_(level, ...) \
    gpi_log_("gpi", level, __FILE__, __func__, __LINE__, __VA_ARGS__)

/** Logs a message at TRACE log level using the current log handler.
 Automatically populates arguments using information in the called context.
*/
#define LOG_TRACE(...) LOG_(GPI_TRACE, __VA_ARGS__)

/** Logs a message at DEBUG log level using the current log handler.
 Automatically populates arguments using information in the called context.
*/
#define LOG_DEBUG(...) LOG_(GPI_DEBUG, __VA_ARGS__)

/** Logs a message at INFO log level using the current log handler.
 Automatically populates arguments using information in the called context.
*/
#define LOG_INFO(...) LOG_(GPI_INFO, __VA_ARGS__)

/** Logs a message at WARN log level using the current log handler.
 Automatically populates arguments using information in the called context.
*/
#define LOG_WARN(...) LOG_(GPI_WARNING, __VA_ARGS__)

/** Logs a message at ERROR log level using the current log handler.
 Automatically populates arguments using information in the called context.
*/
#define LOG_ERROR(...) LOG_(GPI_ERROR, __VA_ARGS__)

/** Logs a message at CRITICAL log level using the current log handler.
 Automatically populates arguments using information in the called context.
*/
#define LOG_CRITICAL(...) LOG_(GPI_CRITICAL, __VA_ARGS__)

#define MAKE_LOG_NAME_(extra_name) \
    (extra_name[0] == '\0' ? "gpi" : "gpi." extra_name)

/** Type of a logger handler function.
 * @param userdata  private implementation data registered with this function
 * @param name      Name of the logger
 * @param level     Level at which to log the message
 * @param pathname  Name of the file where the call site is located
 * @param funcname  Name of the function where the call site is located
 * @param lineno    Line number of the call site
 * @param msg       The message to log, uses C-sprintf-style format specifier
 * @param args      Additional arguments; formatted and inserted in message
 *                  according to format specifier in msg argument
 */
typedef void (*gpi_log_handler_ftype)(void *userdata, const char *name,
                                      int level, const char *pathname,
                                      const char *funcname, long lineno,
                                      const char *msg, va_list args);

/** Type of a logger filter function.
 *
 * Log filter functions test to see if a message would be emitted if logged at
 * the given log level.
 *
 * @param userdata  Private implementation data registered with this function.
 * @param logger    Name of the logger.
 * @param level     Level at which to test if the logger would emit a message.
 * @return `true` if the *logger* is enabled at *level*.
 */
typedef bool (*gpi_log_filter_ftype)(void *userdata, const char *logger,
                                     int level);

/** Type of a logger set level function.
 *
 * Log filter functions test to see if a message would be emitted if logged at
 * the given log level.
 *
 * @param userdata  Private implementation data registered with this function.
 * @param logger    Name of the logger.
 * @param level     Level at which to test if the logger would emit a message.
 * @return `true` if the *logger* is enabled at *level*.
 */
typedef bool (*gpi_log_set_level_ftype)(void *userdata, const char *logger,
                                        int level);

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
GPILOG_EXPORT void gpi_log_(const char *name, int level, const char *pathname,
                            const char *funcname, long lineno, const char *msg,
                            ...);

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
GPILOG_EXPORT void gpi_vlog_(const char *name, int level, const char *pathname,
                             const char *funcname, long lineno, const char *msg,
                             va_list args);

/** Check if a log would be filtered.
 *
 * @param logger Name of the logger.
 * @param level Level at which to test if the logger would emit a message.
 * @return `true` if the *logger* is enabled at *level*.
 */
GPILOG_EXPORT bool gpi_log_filtered(const char *logger, int level);

/** Set the log level of a logger.
 *
 * @param logger Name of the logger.
 * @param level Level to set the logger to.
 * @return The old log level.
 */
GPILOG_EXPORT int gpi_log_set_level(const char *logger, int level);

/** @return The string representation of the GPI log level. */
GPILOG_EXPORT const char *gpi_log_level_to_str(int level);

/** Retrieve the current log handler.
 * @param handler   Location to return current log handler function. If no
 *                  custom logger is registered this will be `NULL`.
 * @param filter    Location to return current log filter function. If no
 *                  custom logger is registered this will be `NULL`.
 * @param set_level Location to return current log set level function. If no
 *                  custom logger is registered this will be `NULL`.
 * @param userdata  Location to return log handler userdata. If no custom
 *                  logger is registered this will be `NULL`.
 */
GPILOG_EXPORT void gpi_get_log_handler(gpi_log_handler_ftype *handler,
                                       gpi_log_filter_ftype *filter,
                                       gpi_log_set_level_ftype *set_level,
                                       void **userdata);

/** Set custom log handler
 * @param handler   Logger handler function.
 * @param filter    Logger level filter function.
 * @param set_level Logger set level function.
 * @param userdata  Data passed to the above functions.
 */
GPILOG_EXPORT void gpi_set_log_handler(gpi_log_handler_ftype handler,
                                       gpi_log_filter_ftype filter,
                                       gpi_log_set_level_ftype set_level,
                                       void *userdata);

/** Clear the current custom log handler and use native logger. */
GPILOG_EXPORT void gpi_clear_log_handler(void);

/*******************************************************************************
 * GPI Native Logger
 *******************************************************************************/

/** Log a message using the native log handler.
 * User is expected to populate all arguments to this function.
 * @param extra_name  Name of the "gpi" child logger, "" for the root logger
 * @param level       Level at which to log the message
 * @param pathname    Name of the file where the call site is located
 * @param funcname    Name of the function where the call site is located
 * @param lineno      Line number of the call site
 * @param msg         The message to log, uses C-sprintf-style format specifier
 * @param ...         Additional arguments; formatted and inserted in message
 *                    according to format specifier in msg argument
 */
#define gpi_native_logger_log(extra_name, level, pathname, funcname, lineno, \
                              ...)                                           \
    gpi_native_logger_log_(MAKE_LOG_NAME_(extra_name), level, pathname,      \
                           funcname, lineno, __VA_ARGS__)

// Don't call this function directly unless the name is "gpi" or starts with
// "gpi."
GPILOG_EXPORT void gpi_native_logger_log_(const char *name, int level,
                                          const char *pathname,
                                          const char *funcname, long lineno,
                                          const char *msg, ...);

/** Log a message using the native log handler.
 * User is expected to populate all arguments to this function.
 * @param extra_name  Name of the "gpi" child logger, "" for the root logger
 * @param level       Level at which to log the message
 * @param pathname    Name of the file where the call site is located
 * @param funcname    Name of the function where the call site is located
 * @param lineno      Line number of the call site
 * @param msg         The message to log, uses C-sprintf-style format specifier
 * @param args        Additional arguments; formatted and inserted in message
 *                    according to format specifier in msg argument
 */
#define gpi_native_logger_vlog(extra_name, level, pathname, funcname, lineno, \
                               msg, args)                                     \
    gpi_native_logger_vlog_(MAKE_LOG_NAME_(extra_name), level, pathname,      \
                            funcname, lineno, msg, args)

// Don't call this function directly unless the name is "gpi" or starts with
// "gpi."
GPILOG_EXPORT void gpi_native_logger_vlog_(const char *name, int level,
                                           const char *pathname,
                                           const char *funcname, long lineno,
                                           const char *msg, va_list args);

/** Check if a message would be filtered by the native logger.
 *
 * @param level     Level at which to test if the logger would emit a message.
 * @return `true` if the *logger* is enabled at *level*.
 */
GPILOG_EXPORT bool gpi_native_logger_filtered(int level);

/** Set minimum logging level of the native logger.
 *
 * If a logging request occurs where the logging level is lower than the level
 * set by this function, it is not logged. Only affects the native logger.
 * @param level     Logging level
 * @return          Previous logging level
 */
GPILOG_EXPORT int gpi_native_logger_set_level(int level);

#ifdef __cplusplus
}
#endif

#endif /* COCOTB_GPI_LOGGING_H_ */
