#ifndef _PYTHON3_COMPAT_H
#define _PYTHON3_COMPAT_H

struct module_state {
    PyObject *error;
};

#if PY_MAJOR_VERSION >= 3
#define PyInt_FromLong PyLong_FromLong
#define PyString_FromString PyUnicode_FromString

#define GETSTATE(m) ((struct module_state*)PyModule_GetState(m))
#define MODULE_ENTRY_POINT PyInit_simulator
#define INITERROR return NULL
#else

#define GETSTATE(m) (&_state)
#define MODULE_ENTRY_POINT initsimulator
#define INITERROR return
#endif

#endif
