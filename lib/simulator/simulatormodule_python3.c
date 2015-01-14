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
    rc |= PyModule_AddIntConstant(simulator, "MEMORY",        gpiMemory);
    rc |= PyModule_AddIntConstant(simulator, "MODULE",        gpiModule);
    rc |= PyModule_AddIntConstant(simulator, "PARAMETER",     gpiParameter);
    rc |= PyModule_AddIntConstant(simulator, "REG",           gpiReg);
    rc |= PyModule_AddIntConstant(simulator, "NET",           gpiNet);
    rc |= PyModule_AddIntConstant(simulator, "NETARRAY",      gpiNetArray);
    if (rc != 0)
        fprintf(stderr, "Failed to add module constants!\n");

    return simulator;
}
