/******************************************************************************
* Copyright (c) 2014 Potential Ventures Ltd
* All rights reserved.
*
* Redistribution and use in source and binary forms, with or without
* modification, are permitted provided that the following conditions are met:
*    * Redistributions of source code must retain the above copyright
*      notice, this list of conditions and the following disclaimer.
*    * Redistributions in binary form must reproduce the above copyright
*      notice, this list of conditions and the following disclaimer in the
*      documentation and/or other materials provided with the distribution.
*    * Neither the name of Potential Ventures Ltd nor the
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

// This file defines the register map for the endian swapper example design.
//
//    byte offset 0:  bit     0  [R/W] byteswap enable
//                    bits 31-1: [N/A] reserved
//    byte offset 4:  bits 31-0: [RO]  packet count


#ifndef __ENDIAN_SWAPPER_REGS_H__
#define __ENDIAN_SWAPPER_REGS_H__


#define ENDIAN_SWAPPER_CONTROL_REG              0
#define IORD_ENDIAN_SWAPPER_CONTROL_REG(base)   \
        IORD(base, ENDIAN_SWAPPER_CONTROL_REG)

#define IOWR_ENDIAN_SWAPPER_CONTROL_REG(base, data)   \
        IOWR(base, ENDIAN_SWAPPER_CONTROL_REG, data)

#define ENDIAN_SWAPPER_ENABLE_MASK              (0x01)
#define ENDIAN_SWAPPER_ENABLE_OFFSET            (0)

#define ENDIAN_SWAPPER_PACKET_COUNT_REG         1
#define IORD_ENDIAN_SWAPPER_PACKET_COUNT_REG(base)   \
        IORD(base, ENDIAN_SWAPPER_PACKET_COUNT_REG)

#define ENDIAN_SWAPPER_PACKET_COUNT_MASK        (0xFFFFFFFF)
#define ENDIAN_SWAPPER_PACKET_COUNT_OFFSET      (0)


#endif // __ENDIAN_SWAPPER_REGS_H__
