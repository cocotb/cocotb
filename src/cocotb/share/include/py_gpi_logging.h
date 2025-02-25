// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#ifndef PY_GPI_LOGGING_H
#define PY_GPI_LOGGING_H

#include <Python.h>

#include "exports.h"

#ifdef PYGPILOG_EXPORTS
#define PYGPILOG_EXPORT COCOTB_EXPORT
#else
#define PYGPILOG_EXPORT COCOTB_IMPORT
#endif

#ifdef __cplusplus
extern "C" {
#endif

PYGPILOG_EXPORT void py_gpi_logger_initialize(PyObject* handler,
                                              PyObject* get_logger);

PYGPILOG_EXPORT void py_gpi_logger_finalize();

extern PYGPILOG_EXPORT PyObject* pEventFn;  // This is gross but I don't care

#ifdef __cplusplus
}
#endif

#endif
