/******************************************************************************
* Copyright (c) 2013 Potential Ventures Ltd
* Copyright (c) 2013 SolarFlare Communications Inc
* All rights reserved.
*
* Redistribution and use in source and binary forms, with or without
* modification, are permitted provided that the following conditions are met:
*    * Redistributions of source code must retain the above copyright
*      notice, this list of conditions and the following disclaimer.
*    * Redistributions in binary form must reproduce the above copyright
*      notice, this list of conditions and the following disclaimer in the
*      documentation and/or other materials provided with the distribution.
*    * Neither the name of Potential Ventures Ltd,
*       SolarFlare Communications Inc nor the
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

#ifndef COCOTB_GPI_H_
#define COCOTB_GPI_H_

/*
Generic Language Interface

This header file defines a Generic Language Interface into any simulator.
Implementations need to implement the underlying functions in gpi_priv.h

The functions are essentially a limited subset of VPI/VHPI/FLI.

Implementation specific notes
=============================

By amazing coincidence, VPI and VHPI are strikingly similar which is obviously
reflected by this header file. Unfortunately, this means that proprietry,
non-standard, less featured language interfaces (for example Mentor FLI) may have
to resort to some hackery, or may not even be capable of implementing a GPI layer.

Because of the lack of ability to register a callback on event change using the FLI,
we have to create a process with the signal on the sensitivity list to imitate a callback.

*/

#include <string.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>
#include <stdbool.h>

#include <gpi_logging.h>

#if defined(__MINGW32__) || defined (__CYGWIN32__)
#  define DLLEXPORT __declspec(dllexport)
#else
#  define DLLEXPORT
#endif

#ifdef __cplusplus
# define EXTERN_C_START extern "C" {
# define EXTERN_C_END }
#else
# define EXTERN_C_START
# define EXTERN_C_END
#endif

#ifndef __GNUC__
# undef  __attribute__
# define __attribute__(x)
#endif


EXTERN_C_START

typedef enum gpi_event_e {
    SIM_INFO = 0,
    SIM_TEST_FAIL = 1,
    SIM_FAIL = 2,
} gpi_event_t;

typedef struct gpi_sim_info_s
{
    int32_t   argc;
    char      **argv;
    char      *product;
    char      *version;
    int32_t   *reserved[4];
} gpi_sim_info_t;

// Define a type for our simulation handle.
typedef struct gpi_sim_hdl_s {
    void *sim_hdl; // Opaque handle for for a simulator object
} gpi_sim_hdl_t, *gpi_sim_hdl;

// Define a type for a simulator callback handle
typedef struct gpi_cb_hdl_s {
    gpi_sim_hdl_t hdl;
    int (*gpi_function)(void *);    // GPI function to callback
    void *gpi_cb_data;              // GPI data supplied to "gpi_function"
} gpi_cb_hdl_t, *gpi_cb_hdl;

// Define a handle type for iterators
typedef struct __gpi_iterator_hdl *gpi_iterator_hdl;

// Functions for controlling/querying the simulation state

// Stop the simulator
void gpi_sim_end(void);


// Returns simulation time as a float. Units are default sim units
void gpi_get_sim_time(uint32_t *high, uint32_t *low);


// Functions for extracting a gpi_sim_hdl to an object
// Returns a handle to the root simulation object,
// Should be freed with gpi_free_handle
gpi_sim_hdl gpi_get_root_handle(const char *name);
gpi_sim_hdl gpi_get_handle_by_name(const char *name, gpi_sim_hdl parent);
gpi_sim_hdl gpi_get_handle_by_index(gpi_sim_hdl parent, uint32_t index);
void gpi_free_handle(gpi_sim_hdl);

// Types that can be passed to the iterator.
//
// Note these are strikingly similar to the VPI types...
#define gpiMemory      29
#define gpiModule      32
#define gpiNet         36
#define gpiParameter   41
#define gpiReg         48
#define gpiNetArray   114

// Functions for iterating over entries of a handle
// Returns an iterator handle which can then be used in gpi_next calls
//
// NB the iterator handle may be NULL if no objects of the requested type are
// found
gpi_iterator_hdl gpi_iterate(uint32_t type, gpi_sim_hdl base);

// Returns NULL when there are no more objects
gpi_sim_hdl gpi_next(gpi_iterator_hdl iterator);



// Functions for querying the properties of a handle

// Caller responsible for freeing the returned string.
// This is all slightly verbose but it saves having to enumerate various value types
// We only care about a limited subset of values.
char *gpi_get_signal_value_binstr(gpi_sim_hdl gpi_hdl);
char *gpi_get_signal_name_str(gpi_sim_hdl gpi_hdl);
char *gpi_get_signal_type_str(gpi_sim_hdl gpi_hdl);



// Functions for setting the properties of a handle
void gpi_set_signal_value_int(gpi_sim_hdl gpi_hdl, int value);
void gpi_set_signal_value_str(gpi_sim_hdl gpi_hdl, const char *str);    // String of binary char(s) [1, 0, x, z]

// The callback registering functions
int gpi_register_timed_callback                  (gpi_sim_hdl, int (*gpi_function)(void *), void *gpi_cb_data, uint64_t time_ps);
int gpi_register_value_change_callback           (gpi_sim_hdl, int (*gpi_function)(void *), void *gpi_cb_data, gpi_sim_hdl gpi_hdl);
int gpi_register_readonly_callback               (gpi_sim_hdl, int (*gpi_function)(void *), void *gpi_cb_data);
int gpi_register_nexttime_callback               (gpi_sim_hdl, int (*gpi_function)(void *), void *gpi_cb_data);
int gpi_register_readwrite_callback              (gpi_sim_hdl, int (*gpi_function)(void *), void *gpi_cb_data);

// Calling convention is that 0 = success and negative numbers a failure
// For implementers of GPI the provided macro GPI_RET(x) is provided
gpi_sim_hdl gpi_create_cb_handle(void);
void gpi_free_cb_handle(gpi_sim_hdl gpi_hdl);

gpi_sim_hdl gpi_create_handle(void);
void gpi_free_handle(gpi_sim_hdl gpi_hdl);

void gpi_deregister_callback(gpi_sim_hdl gpi_hdl);

// Because the internal structures may be different for different implementations
// of GPI we provide a convenience function to extract the callback data
void *gpi_get_callback_data(gpi_sim_hdl gpi_hdl);


#define GPI_RET(_code) \
    if (_code == 1) \
        return 0; \
    else \
        return -1

EXTERN_C_END

#endif /* COCOTB_GPI_H_ */
