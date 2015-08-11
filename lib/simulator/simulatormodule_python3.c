#include "simulatormodule.h"

static PyObject *error_out(PyObject *m)
{
    struct module_state *st = GETSTATE(m);
    PyErr_SetString(st->error, "something bad happened");
    return NULL;
}

static int simulator_traverse(PyObject *m, visitproc visit, void *arg) {
    Py_VISIT(GETSTATE(m)->error);
    return 0;
}

static int simulator_clear(PyObject *m) {
    Py_CLEAR(GETSTATE(m)->error);
    return 0;
}

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    MODULE_NAME,
    NULL,
    sizeof(struct module_state),
    SimulatorMethods,
    NULL,
    simulator_traverse,
    simulator_clear,
    NULL
};

PyMODINIT_FUNC
MODULE_ENTRY_POINT(void)
{
    PyObject* simulator;

    simulator = PyModule_Create(&moduledef);

    if (simulator == NULL) INITERROR;
    struct module_state *st = GETSTATE(simulator);

    st->error = PyErr_NewException(MODULE_NAME ".Error", NULL, NULL);
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
    rc |= PyModule_AddIntConstant(simulator, "STRUCTURE",     GPI_STRUCTURE);
    rc |= PyModule_AddIntConstant(simulator, "REAL",          GPI_REAL);
    if (rc != 0)
        fprintf(stderr, "Failed to add module constants!\n");

    return simulator;
}

