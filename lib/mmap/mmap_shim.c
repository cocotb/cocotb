#include <Python.h>
#include "mmap_shim.h"

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
uint32_t sim_read32(uint32_t address, uint32_t *buffer) {

    printf("In sim_read32\n");

    if (!PyCallable_Check(pRdFunction)) {
        printf("Read function not callable...\n");
        return 0;
    }

    PyObject *call_args = PyTuple_New(1);
    PyObject *rv;

    PyTuple_SetItem(call_args, 0, PyInt_FromLong(address));

    printf("Attempting to call our read function...\n");
    rv = PyObject_CallObject(pRdFunction, call_args);
    printf("Called!\n");
    *buffer = PyInt_AsLong(rv);

    if (PyErr_Occurred())
        PyErr_Print();

    Py_DECREF(rv);
    Py_DECREF(call_args);

    return 1;
}

uint32_t sim_write32(uint32_t address, uint32_t value) {

    if (!PyCallable_Check(pWrFunction))
        return 0;

    PyObject *call_args = PyTuple_New(2);
    PyObject *rv;

    PyTuple_SetItem(call_args, 0, PyInt_FromLong(address));
    PyTuple_SetItem(call_args, 1, PyInt_FromLong(value));

    rv = PyObject_CallObject(pWrFunction, call_args);

    if (PyErr_Occurred())
        PyErr_Print();

    Py_DECREF(rv);
    Py_DECREF(call_args);

    return 1;
}


PyMODINIT_FUNC
initmmap_shim(void)
{
    PyObject* mmap_shim;
    mmap_shim = Py_InitModule("mmap_shim", MMAPShimMethods);
}


