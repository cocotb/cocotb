#ifndef _MMAP_SHIM_MODULE_H
#define _MMAP_SHIM_MODULE_H

#include <Python.h>

static PyObject *set_write_function(PyObject *self, PyObject *args);
static PyObject *set_read_function(PyObject *self, PyObject *args);

static PyMethodDef MMAPShimMethods[] = {
    {"set_write_function", set_write_function, METH_VARARGS, "Set the write function"},
    {"set_read_function",  set_read_function,  METH_VARARGS, "Set the read function"},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

#endif


