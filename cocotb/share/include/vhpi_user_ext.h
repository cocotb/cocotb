// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

/* extensions to vhpi_user.h */

#ifndef VHPI_USER_EXT_H
#define VHPI_USER_EXT_H

#ifdef  __cplusplus
extern "C" {
#endif

/* arguments for vhpiStop or vhpiFinish */
typedef enum
{
  vhpiDiagNone          = 0, /* prints nothing */
  vhpiDiagTimeLoc       = 1, /* prints simulation time and location */
  vhpiDiagTimeLocCPUMem = 2  /* prints simulation time, location and statistics about CPU and memory usage */
} vhpiDiagT;

#ifdef  __cplusplus
}
#endif

#endif /* VHPI_USER_EXT_H */
