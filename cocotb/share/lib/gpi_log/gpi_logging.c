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
* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
* ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
* WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
* DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
* DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
* (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
* LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
* ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
* (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
* SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
******************************************************************************/

#include <Python.h>
#include "../compat/python3_compat.h"
#include <gpi_logging.h>

// Used to log using the standard python mechanism
static PyObject *pLogHandler = NULL;
static PyObject *pLogFilter = NULL;
static enum gpi_log_levels local_level = GPIInfo;

void set_log_handler(void *handler)
{
    pLogHandler = (PyObject *)handler;      // Note: This function steals a reference to handler.
}

void clear_log_handler(void)
{
    Py_XDECREF(pLogHandler);
    pLogHandler = NULL;
}

void set_log_filter(void *filter)
{
    pLogFilter = (PyObject *)filter;        // Note: This function steals a reference to filter.
}

void clear_log_filter(void)
{
    Py_XDECREF(pLogFilter);
    pLogFilter = NULL;
}

void set_log_level(enum gpi_log_levels new_level)
{
    local_level = new_level;
}

// Decode the level into a string matching the Python interpretation
struct _log_level_table {
    long level;
    const char *levelname;
};

static struct _log_level_table log_level_table [] = {
    { 10,       "DEBUG"         },
    { 20,       "INFO"          },
    { 30,       "WARNING"       },
    { 40,       "ERROR"         },
    { 50,       "CRITICAL"      },
    { 0,        NULL}
};

const char *log_level(long level)
{
  struct _log_level_table *p;
  const char *str = "------";

  for (p=log_level_table; p->levelname; p++) {
    if (level == p->level) {
      str = p->levelname;
      break;
    }
  }
  return str;
}

// We keep this module global to avoid reallocation
// we do not need to worry about locking here as
// are single threaded and can not have multiple calls
// into gpi_log at once.
#define LOG_SIZE    512
static char log_buff[LOG_SIZE];

/**
 * @name    GPI logging
 * @brief   Write a log message using cocotb SimLog class
 * @ingroup python_c_api
 *
 * GILState before calling: Unknown
 *
 * GILState after calling: Unknown
 *
 * Makes one call to PyGILState_Ensure and one call to PyGILState_Release
 *
 * If the Python logging mechanism is not initialised, dumps to `stderr`.
 *
 */
void gpi_log(const char *name, long level, const char *pathname, const char *funcname, long lineno, const char *msg, ...)
{
    /* We first check that the log level means this will be printed
     * before going to the expense of processing the variable
     * arguments
     */
    va_list ap;
    int n;

    if (!pLogHandler) {
        if (level >= GPIInfo) {
            va_start(ap, msg);
            n = vsnprintf(log_buff, LOG_SIZE, msg, ap);
            va_end(ap);

            if (n < 0) {
               fprintf(stderr, "Log message construction failed\n");
            }

            fprintf(stdout, "     -.--ns ");
            fprintf(stdout, "%-9s", log_level(level));
            fprintf(stdout, "%-35s", name);

            n = strlen(pathname);
            if (n > 20) {
                fprintf(stdout, "..%18s:", (pathname + (n - 18)));
            } else {
                fprintf(stdout, "%20s:", pathname);
            }

            fprintf(stdout, "%-4ld", lineno);
            fprintf(stdout, " in %-31s ", funcname);
            fprintf(stdout, "%s", log_buff);
            fprintf(stdout, "\n");
            fflush(stdout);
        }
        return;
    }

    if (level < local_level)
        return;

    PyGILState_STATE gstate = PyGILState_Ensure();

    // Declared here in order to be initialized before any goto statements and refcount cleanup
    PyObject *logger_name_arg = NULL, *filename_arg = NULL, *lineno_arg = NULL, *msg_arg = NULL, *function_arg = NULL;

    PyObject *level_arg = PyLong_FromLong(level);                  // New reference
    if (level_arg == NULL) {
        goto error;
    }

    logger_name_arg = PyUnicode_FromString(name);      // New reference
    if (logger_name_arg == NULL) {
        goto error;
    }

    PyObject *filter_ret = PyObject_CallFunctionObjArgs(pLogFilter, logger_name_arg, level_arg, NULL);
    if (filter_ret == NULL) {
        goto error;
    }

    int is_enabled = PyObject_IsTrue(filter_ret);
    Py_DECREF(filter_ret);
    if (is_enabled < 0) {
        /* A python exception occured while converting `filter_ret` to bool */
        goto error;
    }

    if (!is_enabled) {
        goto ok;
    }

    // Ignore truncation
    va_start(ap, msg);
    n = vsnprintf(log_buff, LOG_SIZE, msg, ap);
    va_end(ap);

    filename_arg = PyUnicode_FromString(pathname);      // New reference
    if (filename_arg == NULL) {
        goto error;
    }

    lineno_arg = PyLong_FromLong(lineno);               // New reference
    if (lineno_arg == NULL) {
        goto error;
    }

    msg_arg = PyUnicode_FromString(log_buff);           // New reference
    if (msg_arg == NULL) {
        goto error;
    }

    function_arg = PyUnicode_FromString(funcname);      // New reference
    if (function_arg == NULL) {
        goto error;
    }

    // Log function args are logger_name, level, filename, lineno, msg, function
    PyObject *handler_ret = PyObject_CallFunctionObjArgs(pLogHandler, logger_name_arg, level_arg, filename_arg, lineno_arg, msg_arg, function_arg, NULL);
    if (handler_ret == NULL) {
        goto error;
    }
    Py_DECREF(handler_ret);

    goto ok;
error:
    PyErr_Print();
    LOG_ERROR("Error calling Python logging function from C");
ok:
    Py_XDECREF(logger_name_arg);
    Py_XDECREF(level_arg);
    Py_XDECREF(filename_arg);
    Py_XDECREF(lineno_arg);
    Py_XDECREF(msg_arg);
    Py_XDECREF(function_arg);
    PyGILState_Release(gstate);
}
