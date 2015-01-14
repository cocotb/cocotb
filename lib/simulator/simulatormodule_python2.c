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
    rc |= PyModule_AddIntConstant(simulator, "MEMORY",        gpiMemory);
    rc |= PyModule_AddIntConstant(simulator, "MODULE",        gpiModule);
    rc |= PyModule_AddIntConstant(simulator, "PARAMETER",     gpiParameter);
    rc |= PyModule_AddIntConstant(simulator, "REG",           gpiReg);
    rc |= PyModule_AddIntConstant(simulator, "NET",           gpiNet);
    rc |= PyModule_AddIntConstant(simulator, "NETARRAY",      gpiNetArray);
    if (rc != 0)
        fprintf(stderr, "Failed to add module constants!\n");
}
