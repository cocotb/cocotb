// Copyright cocotb contributors
// Copyright (c) 2013, 2019 Potential Ventures Ltd
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

/* extensions to vpi_user.h */

#ifndef VPI_USER_EXT_H
#define VPI_USER_EXT_H

#ifdef  __cplusplus
extern "C" {
#endif

/* used by Cadence Xcelium for packed unions */
#define vpiUnionNet          525

/* used by Cadence Xcelium for Verilog-AMS */
#define vpiRealNet           526
#define vpiInterconnectNet   533
#define vpiInterconnectArray 534

/* arguments for vpiStop or vpiFinish */
#define vpiDiagNone               0  /* prints nothing */
#define vpiDiagTimeLoc            1  /* prints simulation time and location */
#define vpiDiagTimeLocCPUMem      2  /* prints simulation time, location and
                                        statistics about CPU and memory usage */

#ifdef  __cplusplus
}
#endif

#endif /* VPI_USER_EXT_H */
