/******************************************************************************
* Copyright (c) 2013, 2019 Potential Ventures Ltd
* All rights reserved.
*
* Redistribution and use in source and binary forms, with or without
* modification, are permitted provided that the following conditions are met:
*    * Redistributions of source code must retain the above copyright
*      notice, this list of conditions and the following disclaimer.
*    * Redistributions in binary form must reproduce the above copyright
*      notice, this list of conditions and the following disclaimer in the
*      documentation and/or other materials provided with the distribution.
*    * Neither the name of Potential Ventures Ltd
*      names of its contributors may be used to endorse or promote products
*      derived from this software without specific prior written permission.
*
* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
* ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
* WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
* DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
* DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
* (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
* LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
* ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
* (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
* SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
******************************************************************************/

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
