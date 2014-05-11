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

// Implementation of the HAL
#include "io.h"
#include "endian_swapper_regs.h"
#include "endian_swapper_hal.h"


endian_swapper_state_t endian_swapper_init(unsigned int base)
{
    endian_swapper_state_t state;
    state.base = base;
    return state;
}


int endian_swapper_enable(endian_swapper_state_t *state)
{
    unsigned int control;
    control = IORD_ENDIAN_SWAPPER_CONTROL_REG(state->base);
    control |= ENDIAN_SWAPPER_ENABLE_MASK;
    IOWR_ENDIAN_SWAPPER_CONTROL_REG(state->base, control);
    return 0;
}


int endian_swapper_disable(endian_swapper_state_t *state)
{
    unsigned int control;
    control = IORD_ENDIAN_SWAPPER_CONTROL_REG(state->base);
    control ^= ENDIAN_SWAPPER_ENABLE_MASK;
    IOWR_ENDIAN_SWAPPER_CONTROL_REG(state->base, control);
    return 0;
}


int endian_swapper_get_count(endian_swapper_state_t *state)
{
    return IORD_ENDIAN_SWAPPER_PACKET_COUNT_REG(state->base);
}

