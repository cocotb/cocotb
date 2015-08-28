#include "simulatormodule.h"

char error_module[] = MODULE_NAME ".Error";
static struct module_state _state;

static PyObject *error_out(PyObject *m)
{
    struct module_state *st = GETSTATE(m);
    PyErr_SetString(st->error, "something bad happened");
    return NULL;
}

PyMODINIT_FUNC
MODULE_ENTRY_POINT(void)
{
    PyObject* simulator;

    simulator = Py_InitModule(MODULE_NAME, SimulatorMethods);

    if (simulator == NULL) INITERROR;
    struct module_state *st = GETSTATE(simulator);

    st->error = PyErr_NewException((char *) &error_module, NULL, NULL);
    if (st->error == NULL) {
        Py_DECREF(simulator);
        INITERROR;
    }

    add_module_constants(simulator);
}
