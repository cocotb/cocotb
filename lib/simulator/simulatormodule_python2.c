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

    // Make the GPI constants accessible from the C world
    int rc = 0;
    rc |= PyModule_AddIntConstant(simulator, "UNKNOWN",       GPI_UNKNOWN);
    rc |= PyModule_AddIntConstant(simulator, "MEMORY",        GPI_MEMORY);
    rc |= PyModule_AddIntConstant(simulator, "MODULE",        GPI_MODULE);
    rc |= PyModule_AddIntConstant(simulator, "NET",           GPI_NET);
    rc |= PyModule_AddIntConstant(simulator, "PARAMETER",     GPI_PARAMETER);
    rc |= PyModule_AddIntConstant(simulator, "REG",           GPI_REGISTER);
    rc |= PyModule_AddIntConstant(simulator, "NETARRAY",      GPI_ARRAY);
    rc |= PyModule_AddIntConstant(simulator, "ENUM",          GPI_ENUM);
    rc |= PyModule_AddIntConstant(simulator, "ENUM",          GPI_STRUCTURE);
    if (rc != 0)
        fprintf(stderr, "Failed to add module constants!\n");
}
