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

/* Py_SETREF was added in 3.5.2, and only if Py_LIMITED_API is absent */
#ifndef Py_SETREF
    #define Py_SETREF(op, op2)                      \
        do {                                        \
            PyObject *_py_tmp = (PyObject *)(op);   \
            (op) = (op2);                           \
            Py_DECREF(_py_tmp);                     \
        } while (0)
#endif


// Python read function just takes an offset in bytes and a buffer
static PyObject *pWrFunction = Py_None;
// Python read function just takes an offset in bytes and returns a value
static PyObject *pRdFunction = Py_None;

// Functions called by Python
static PyObject *set_write_function(PyObject *self, PyObject *args)
{
    PyObject *func;
    if (!PyArg_ParseTuple(args, "O:set_write_function", &func)) {
        return NULL;
    }
    Py_INCREF(func);
    Py_SETREF(pWrFunction, func);

    Py_RETURN_NONE;
}

static PyObject *set_read_function(PyObject *self, PyObject *args)
{
    PyObject *func;
    if (!PyArg_ParseTuple(args, "O:set_read_function", &func)) {
        return NULL;
    }
    Py_INCREF(func);
    Py_SETREF(pRdFunction, func);

    Py_RETURN_NONE;
}


// Functions called by C (exported in a shared library)
unsigned int IORD(unsigned int base, unsigned int address)
{
    PyObject *rv = PyObject_CallFunction(pRdFunction, "I", base + address);
    if (rv == NULL) {
        PyErr_WriteUnraisable(NULL);
        return 0;
    }

    long value = PyInt_AsLong(rv);
    Py_DECREF(rv);

    if (value == -1 && PyErr_Occurred()) {
        PyErr_WriteUnraisable(NULL);
        return 0;
    }

    return (unsigned int)value;
}

int IOWR(unsigned int base, unsigned int address, unsigned int value)
{
    /* `I` is `unsigned int` */
    PyObject *rv = PyObject_CallFunction(pWrFunction, "II", base + address, value);
    if (rv == NULL) {
        PyErr_WriteUnraisable(NULL);
        return 0;
    }
    Py_DECREF(rv);
    return 0;
}

static struct PyModuleDef io_module =
{
    PyModuleDef_HEAD_INIT,
    "io_module", // name
    "", // documentation
    -1, // amount of memory to allocate for module when using sub-interpreters,
        // -1 means module has a global state
    io_module_methods
};

PyMODINIT_FUNC PyInit_io_module(void)
{
    return PyModule_Create(&io_module);
}

