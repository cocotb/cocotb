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
static PyObject *pLogHandler;
static PyObject *pLogFilter;
static enum gpi_log_levels local_level = GPIInfo;

void set_log_handler(void *handler)
{
    pLogHandler = (PyObject *)handler;
    Py_INCREF(pLogHandler);
}

void set_log_filter(void *filter)
{
    pLogFilter = (PyObject *)filter;
    Py_INCREF(pLogFilter);
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
 * If the Python logging mechanism is not initialised, dumps to stderr.
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

            if (0 > n) {
               fprintf(stderr, "Log message construction failed\n");
            }
 
            fprintf(stdout, "     -.--ns ");
            fprintf(stdout, "%-9s", log_level(level));
            fprintf(stdout, "%-35s", name);
            fprintf(stdout, "%20s:", pathname);
            fprintf(stdout, "%-4ld", lineno);
            fprintf(stdout, " in %-31s ", funcname);
            fprintf(stdout, "%s", log_buff);
            fprintf(stdout, "\n");
        }
        return;
    }

    if (level < local_level)
        return;

    // Ignore truncation
    // calling args is level, filename, lineno, msg, function
    //
    PyGILState_STATE gstate = PyGILState_Ensure();

    PyObject *check_args = PyTuple_New(1);
    PyTuple_SetItem(check_args, 0, PyLong_FromLong(level));
    PyObject *retuple = PyObject_CallObject(pLogFilter, check_args);

    if (retuple != Py_True) {
        Py_DECREF(check_args);
        PyGILState_Release(gstate);
        return;
    }

    Py_DECREF(retuple);
    Py_DECREF(check_args);

    va_start(ap, msg);
    n = vsnprintf(log_buff, LOG_SIZE, msg, ap);
    va_end(ap);

    PyObject *call_args = PyTuple_New(5);
    PyTuple_SetItem(call_args, 0, PyLong_FromLong(level));           // Note: This function steals a reference.
    PyTuple_SetItem(call_args, 1, PyUnicode_FromString(pathname));   // Note: This function steals a reference.
    PyTuple_SetItem(call_args, 2, PyLong_FromLong(lineno));          // Note: This function steals a reference.
    PyTuple_SetItem(call_args, 3, PyUnicode_FromString(log_buff));   // Note: This function steals a reference.
    PyTuple_SetItem(call_args, 4, PyUnicode_FromString(funcname));

    retuple = PyObject_CallObject(pLogHandler, call_args);

    if (retuple != Py_True) {
        PyGILState_Release(gstate);
        return;
    }

    Py_DECREF(call_args);
    Py_DECREF(retuple);

    PyGILState_Release(gstate);
}
