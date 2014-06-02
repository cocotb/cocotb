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

// Implementation of the HAL that uses mmap
#include <sys/mman.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <errno.h>
#include <stdint.h>
#include <stdlib.h>     // Remove

#include "endian_swapper_regs.h"
#include "endian_swapper_hal.h"

#define PAGE_SIZE sysconf(_SC_PAGESIZE)

typedef struct {
    uint32_t            control;
    uint32_t            count;
} endian_swapper_regs_t;

endian_swapper_state_t endian_swapper_init(unsigned int base)
{
    int rc;
    void *pointer;
    endian_swapper_state_t state;
    state.map = NULL;

    state.fd = open("/dev/mem", O_RDWR);
    if (state.fd < 0) {
        printf("Couldn't open /dev/mem\n");
        return state;
    }

    state.map = mmap(NULL, PAGE_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, 
                     state.fd, base);

    if (state.map == MAP_FAILED) {
            printf("mmap failed\n");
            close(state.fd);
            state.map = NULL;
            return state;
    }
    state.base = base;
    return state;
}


int endian_swapper_enable(endian_swapper_state_t *state)
{
    if (NULL == state->map) {
        printf("Not yet mapped\n");
        fflush(stdout);
        return -1;
    }

    endian_swapper_regs_t *regs = (endian_swapper_regs_t *)(state->map);
    regs->control |= 1;
    return 0;
}


int endian_swapper_disable(endian_swapper_state_t *state)
{
    if (NULL == state->map) {
        printf("Not yet mapped\n");
        fflush(stdout);
        return -1;
    }

    endian_swapper_regs_t *regs = (endian_swapper_regs_t *)(state->map);
    regs->control ^= 1;
    return 0;
}


int endian_swapper_get_count(endian_swapper_state_t *state)
{
    if (NULL == state->map) {
        printf("Not yet mapped\n");
        fflush(stdout);
        return -1;
    }
    endian_swapper_regs_t *regs = (endian_swapper_regs_t *)(state->map);
    return regs->count;
}


int main(void)
{
    printf("Initialising endian swapper\n");
    fflush(stdout);
    endian_swapper_state_t state = endian_swapper_init(0);
    endian_swapper_enable(&state);
    printf("Packet count: %d\n", endian_swapper_get_count(&state));
    return 0;
}


