/******************************************************************************
* Copyright (c) 2014 Potential Ventures Ltd
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

// This module bridges between the testbench world and the HAL

// We export a READ/WRITE function with the same name as normal hardware
// access


#include "io.h"

#include <Python.h>
#include "io_module.h"

// Python read function just takes an offset in bytes and a buffer
static PyObject *pWrFunction;
// Python read function just takes an offset in bytes and returns a value
static PyObject *pRdFunction;

// Functions called by Python
static PyObject *set_write_function(PyObject *self, PyObject *args) {

    pWrFunction = PyTuple_GetItem(args, 0);
    Py_INCREF(pWrFunction);

    PyObject *retstr = Py_BuildValue("s", "OK!");
    return retstr;
}

static PyObject *set_read_function(PyObject *self, PyObject *args) {

    pRdFunction = PyTuple_GetItem(args, 0);
    Py_INCREF(pRdFunction);

    PyObject *retstr = Py_BuildValue("s", "OK!");
    return retstr;
}


// Functions called by C (exported in a shared library)
unsigned int IORD(unsigned int base, unsigned int address) {

    unsigned int value;

    if (!PyCallable_Check(pRdFunction)) {
        printf("Read function not callable...\n");
        return 0;
    }

    PyObject *call_args = PyTuple_New(1);
    PyObject *rv;

    PyTuple_SetItem(call_args, 0, PyInt_FromLong(base + address));

    rv = PyObject_CallObject(pRdFunction, call_args);
    value = PyInt_AsLong(rv);

    if (PyErr_Occurred())
        PyErr_Print();

    Py_DECREF(rv);
    Py_DECREF(call_args);

    return value;
}

int IOWR(unsigned int base, unsigned int address, unsigned int value)
{

    if (!PyCallable_Check(pWrFunction)) {
        printf("Write function isn't callable...\n");
        return -1;
    }

    PyObject *call_args = PyTuple_New(2);
    PyObject *rv;

    PyTuple_SetItem(call_args, 0, PyInt_FromLong(base + address));
    PyTuple_SetItem(call_args, 1, PyInt_FromLong(value));

    rv = PyObject_CallObject(pWrFunction, call_args);

    if (PyErr_Occurred())
        PyErr_Print();

    Py_DECREF(rv);
    Py_DECREF(call_args);

    return 0;
}

PyMODINIT_FUNC
initio_module(void)
{
    PyObject* io_module;
    io_module = Py_InitModule("io_module", io_module_methods);
    if (!io_module) {
        printf("Failed to load io_module\n");
        exit(1);
    }
}

