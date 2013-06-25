/******************************************************************************
* Copyright (c) 2013 Potential Ventures Ltd
* All rights reserved.
*
* Redistribution and use in source and binary forms, with or without
* modification, are permitted provided that the following conditions are met:
*    * Redistributions of source code must retain the above copyright
*      notice, this list of conditions and the following disclaimer.
*    * Redistributions in binary form must reproduce the above copyright
*      notice, this list of conditions and the following disclaimer in the
*      documentation and/or other materials provided with the distribution.
*    * Neither the name of Potential Ventures Ltd nor the
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

// Used to log using the standard python mechanism
static PyObject *pLogHandler;
static PyObject *pLogFilter;
static PyObject *pLogMakeRecord;

void set_log_handler(void *handler)
{
    pLogHandler = (PyObject *)handler;
    Py_INCREF(pLogHandler);
}

void set_make_record(void *makerecord)
{
    pLogMakeRecord = (PyObject *)makerecord;
    Py_INCREF(pLogMakeRecord);
}

void set_log_filter(void *filter)
{
    pLogFilter = (PyObject *)filter;
    Py_INCREF(pLogFilter);
}


/**
 * @name    GPI logging
 * @brief   Write a log message using Python logging module
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
 * TODO: correct handling of VARARGS for format strings
 */
void gpi_log(const char *name, long level, const char *pathname, const char *funcname, long lineno, const char *msg, ...)
{

    if (pLogMakeRecord != NULL && pLogHandler != NULL && pLogFilter != NULL) {

        //Ensure that the current thread is ready to callthe Python C API
        PyGILState_STATE gstate = PyGILState_Ensure();

        if (PyCallable_Check(pLogMakeRecord) && PyCallable_Check(pLogHandler)) {
            PyObject *pArgs = PyTuple_New(7);
            PyTuple_SetItem(pArgs, 0, PyString_FromString(name));       // Note: This function “steals” a reference to o.
            PyTuple_SetItem(pArgs, 1, PyInt_FromLong(level));           // Note: This function “steals” a reference to o.
            PyTuple_SetItem(pArgs, 2, PyString_FromString(pathname));   // Note: This function “steals” a reference to o.
            PyTuple_SetItem(pArgs, 3, PyInt_FromLong(lineno));          // Note: This function “steals” a reference to o.
            PyTuple_SetItem(pArgs, 4, PyString_FromString(msg));        // Note: This function “steals” a reference to o.
            PyTuple_SetItem(pArgs, 5, Py_None); //NONE
            PyTuple_SetItem(pArgs, 6, Py_None); //NONE

            Py_INCREF(Py_None);                 // Need to provide a reference to steal
            Py_INCREF(Py_None);                 // Need to provide a reference to steal

            PyObject *pDict;
            pDict = Py_BuildValue("{s:s}", "func", funcname);

            PyObject *pLogRecord = PyObject_Call(pLogMakeRecord, pArgs, pDict);
            Py_DECREF(pArgs);
            Py_DECREF(pDict);

            PyObject *pLogArgs = PyTuple_Pack(1, pLogRecord);
            Py_DECREF(pLogRecord);

            // Filter here
#ifdef NO_FILTER
            PyObject *pShouldFilter = PyObject_CallObject(pLogFilter, pLogArgs);
            if (pShouldFilter == Py_True) {
#endif
                PyObject *pLogResult = PyObject_CallObject(pLogHandler, pLogArgs);
                Py_DECREF(pLogResult);
#ifdef NO_FILTER
            }

            Py_DECREF(pShouldFilter);
#endif
            Py_DECREF(pLogArgs);

        } else {
            PyGILState_Release(gstate);
            goto clog;

            fprintf(stderr, "ERROR: Unable to log into python - logging functions aren't callable\n");
            fprintf(stderr, "%s", msg);
            fprintf(stderr, "\n");

        }

        // Matching call to release GIL
        PyGILState_Release(gstate);

    // Python logging not available, just dump to stdout (No filtering)
    } else {
clog:
        fprintf(stdout, "     -.--ns");
        fprintf(stdout, " %2ld", level);                // FIXME: Print msglevel DEBUG INFO etc.
        fprintf(stdout, "%16s", name);
        fprintf(stdout, "%45s:", pathname);
        fprintf(stdout, "%4ld", lineno);
        fprintf(stdout, " in %s\t", funcname);
        fprintf(stdout, "%25s", msg);
        fprintf(stdout, "\n");
    }

    return;
}
