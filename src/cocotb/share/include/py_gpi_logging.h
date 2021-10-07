// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#ifndef PY_GPI_LOGGING_H
#define PY_GPI_LOGGING_H

#include <exports.h>
#ifdef PYGPILOG_EXPORTS
#define PYGPILOG_EXPORT COCOTB_EXPORT
#else
#define PYGPILOG_EXPORT COCOTB_IMPORT
#endif

#define PY_GPI_LOG_SIZE 1024

#ifdef __cplusplus
extern "C" {
#endif

PYGPILOG_EXPORT void py_gpi_logger_set_level(int level);

PYGPILOG_EXPORT void py_gpi_logger_initialize(PyObject* handler,
                                              PyObject* filter);

PYGPILOG_EXPORT void py_gpi_logger_finalize();

#ifdef __cplusplus
}
#endif

#endif
