/******************************************************************************
 * Copyright (c) 2013 Potential Ventures Ltd
 * Copyright (c) 2013 SolarFlare Communications Inc
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *    * Redistributions of source code must retain the above copyright
 *      notice, this list of conditions and the following disclaimer.
 *    * Redistributions in binary form must reproduce the above copyright
 *      notice, this list of conditions and the following disclaimer in the
 *      documentation and/or other materials provided with the distribution.
 *    * Neither the name of Potential Ventures Ltd,
 *       SolarFlare Communications Inc nor the
 *      names of its contributors may be used to endorse or promote products
 *      derived from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
 * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 ******************************************************************************/

#ifndef COCOTB_GPI_LOGGING_H_
#define COCOTB_GPI_LOGGING_H_

#include <exports.h>
#ifdef GPILOG_EXPORTS
#define GPILOG_EXPORT COCOTB_EXPORT
#else
#define GPILOG_EXPORT COCOTB_IMPORT
#endif

#include <cstdarg>

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
enum gpi_log_levels {
    GPITrace = 5,   ///< Prints `TRACE` by default. Information about execution
                    ///< of simulator callbacks and Python / simulator contexts
    GPIDebug = 10,  ///< Prints `DEBUG` by default. Verbose information, useful
                    ///< for debugging
    GPIInfo = 20,  ///< Prints `INFO` by default. Information about major events
                   ///< in the current program
    GPIWarning = 30,  ///< Prints `WARN` by default. Encountered a recoverable
                      ///< bug, or information about surprising behavior
    GPIError = 40,    ///< Prints `ERROR` by default. An unrecoverable error
    GPICritical = 50  ///< Prints `CRITICAL` by default. An unrecoverable error,
                      ///< to be followed by immediate simulator shutdown
};

/** Logs a message at the given log level using the current log handler.
    Automatically populates arguments using information in the called context.
    @param level The level at which to log the message
 */
#define LOG_(level, ...) \
    gpi_log("gpi", level, __FILE__, __func__, __LINE__, __VA_ARGS__);

/** Logs a message at TRACE log level using the current log handler.
    Automatically populates arguments using information in the called context.
 */
#define LOG_TRACE(...) LOG_(GPITrace, __VA_ARGS__)

/** Logs a message at DEBUG log level using the current log handler.
    Automatically populates arguments using information in the called context.
 */
#define LOG_DEBUG(...) LOG_(GPIDebug, __VA_ARGS__)

/** Logs a message at INFO log level using the current log handler.
    Automatically populates arguments using information in the called context.
 */
#define LOG_INFO(...) LOG_(GPIInfo, __VA_ARGS__);

/** Logs a message at WARN log level using the current log handler.
    Automatically populates arguments using information in the called context.
 */
#define LOG_WARN(...) LOG_(GPIWarning, __VA_ARGS__);

/** Logs a message at ERROR log level using the current log handler.
    Automatically populates arguments using information in the called context.
 */
#define LOG_ERROR(...) LOG_(GPIError, __VA_ARGS__);

/** Logs a message at CRITICAL log level using the current log handler.
    Automatically populates arguments using information in the called context.
 */
#define LOG_CRITICAL(...) LOG_(GPICritical, __VA_ARGS__);

/** Type of a log handler function.
    @param userdata  private implementation data registered with this function
    @param name      Name of the logger
    @param level     Level at which to log the message
    @param pathname  Name of the file where the call site is located
    @param funcname  Name of the function where the call site is located
    @param lineno    Line number of the call site
    @param msg       The message to log, uses C-sprintf-style format specifier
    @param args      Additional arguments; formatted and inserted in message
                     according to format specifier in msg argument
 */
typedef void(gpi_log_handler_type)(void *userdata, const char *name, int level,
                                   const char *pathname, const char *funcname,
                                   long lineno, const char *msg, va_list args);

/** Log a message using the currently registered log handler.
    User is expected to populate all arguments to this function.
    @param name      Name of the logger
    @param level     Level at which to log the message
    @param pathname  Name of the file where the call site is located
    @param funcname  Name of the function where the call site is located
    @param lineno    Line number of the call site
    @param msg       The message to log, uses C-sprintf-style format specifier
    @param ...       Additional arguments; formatted and inserted in message
                     according to format specifier in msg argument
 */
GPILOG_EXPORT void gpi_log(const char *name, int level, const char *pathname,
                           const char *funcname, long lineno, const char *msg,
                           ...);

/** Log a message using the currently registered log handler.
    User is expected to populate all arguments to this function.
    @param name      Name of the logger
    @param level     Level at which to log the message
    @param pathname  Name of the file where the call site is located
    @param funcname  Name of the function where the call site is located
    @param lineno    Line number of the call site
    @param msg       The message to log, uses C-sprintf-style format specifier
    @param args      Additional arguments; formatted and inserted in message
                     according to format specifier in msg argument
 */
GPILOG_EXPORT void gpi_vlog(const char *name, int level, const char *pathname,
                            const char *funcname, long lineno, const char *msg,
                            va_list args);

/** Retrieve the current log handler.
    @param handler  Location to return current log handler. If no custom logger
                    is registered this will be `NULL`.
    @param userdata Location to return log handler userdata
 */
GPILOG_EXPORT void gpi_get_log_handler(gpi_log_handler_type **handler,
                                       void **userdata);

/** Set custom log handler
    @param handler   Handler function to call when the GPI logs a message
    @param userdata  Data to pass to the handler function when logging a message
 */
GPILOG_EXPORT void gpi_set_log_handler(gpi_log_handler_type *handler,
                                       void *userdata);

/** Clear the current custom log handler and use native logger
 */
GPILOG_EXPORT void gpi_clear_log_handler(void);

/** Log a message using the native log handler.
    User is expected to populate all arguments to this function.
    @param name      Name of the logger
    @param level     Level at which to log the message
    @param pathname  Name of the file where the call site is located
    @param funcname  Name of the function where the call site is located
    @param lineno    Line number of the call site
    @param msg       The message to log, uses C-sprintf-style format specifier
    @param ...       Additional arguments; formatted and inserted in message
                     according to format specifier in msg argument
 */
GPILOG_EXPORT void gpi_native_logger_log(const char *name, int level,
                                         const char *pathname,
                                         const char *funcname, long lineno,
                                         const char *msg, ...);

/** Log a message using the native log handler.
    User is expected to populate all arguments to this function.
    @param name      Name of the logger
    @param level     Level at which to log the message
    @param pathname  Name of the file where the call site is located
    @param funcname  Name of the function where the call site is located
    @param lineno    Line number of the call site
    @param msg       The message to log, uses C-sprintf-style format specifier
    @param args      Additional arguments; formatted and inserted in message
                     according to format specifier in msg argument
 */
GPILOG_EXPORT void gpi_native_logger_vlog(const char *name, int level,
                                          const char *pathname,
                                          const char *funcname, long lineno,
                                          const char *msg, va_list args);

/** Set minimum logging level of the native logger.
    If a logging request occurs where the logging level is lower than the level
    set by this function, it is not logged. Only affects the native logger.
    @param level     Logging level
    @return          Previous logging level
 */
GPILOG_EXPORT int gpi_native_logger_set_level(int level);

#ifdef __cplusplus
}
#endif

#endif /* COCOTB_GPI_LOGGING_H_ */
