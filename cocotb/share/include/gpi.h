/******************************************************************************
 * Copyright (c) 2013, 2018 Potential Ventures Ltd
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
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
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
non-standard, less featured language interfaces (for example Mentor FLI) may
have to resort to some hackery.

Because of the lack of ability to register a callback on event change using the
FLI, we have to create a process with the signal on the sensitivity list to
imitate a callback.

*/

#include <exports.h>
#ifdef GPI_EXPORTS
#define GPI_EXPORT COCOTB_EXPORT
#else
#define GPI_EXPORT COCOTB_IMPORT
#endif

#include <gpi_logging.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/*
 * Declare the handle types.
 *
 * We want these handles to be opaque pointers, since their layout is not
 * exposed to C. We do this by using incomplete types. The assumption being
 * made here is that `sizeof(some_cpp_class*) == sizeof(some_c_struct*)`, which
 * is true on all reasonable platforms.
 */
#ifdef __cplusplus
/* In C++, we use forward-declarations of the types in gpi_priv.h as our
 * incomplete types, as this avoids the need for any casting in GpiCommon.cpp.
 */
class GpiObjHdl;
class GpiCbHdl;
class GpiIterator;
typedef GpiObjHdl *gpi_sim_hdl;
typedef GpiCbHdl *gpi_cb_hdl;
typedef GpiIterator *gpi_iterator_hdl;
#else
/* In C, we declare some incomplete struct types that we never complete.
 * The names of these are irrelevant, but for simplicity they match the C++
 * names.
 */
struct GpiObjHdl;
struct GpiCbHdl;
struct GpiIterator;
typedef struct GpiObjHdl *gpi_sim_hdl;
typedef struct GpiCbHdl *gpi_cb_hdl;
typedef struct GpiIterator *gpi_iterator_hdl;
#endif

#ifdef __cplusplus
extern "C" {
#endif

// Functions for controlling/querying the simulation state

/**
 * Returns 1 if there is a registered GPI implementation, 0 otherwise.
 *
 * Useful for checking if a simulator is running.
 */
GPI_EXPORT bool gpi_has_registered_impl(void);

// Stop the simulator
GPI_EXPORT void gpi_sim_end(void);

// Returns simulation time as two uints. Units are default sim units
GPI_EXPORT void gpi_get_sim_time(uint32_t *high, uint32_t *low);
GPI_EXPORT void gpi_get_sim_precision(int32_t *precision);

/**
 * Returns a string with the running simulator product information
 *
 * @return simulator product string
 */
GPI_EXPORT const char *gpi_get_simulator_product(void);

/**
 * Returns a string with the running simulator version
 *
 * @return simulator version string
 */
GPI_EXPORT const char *gpi_get_simulator_version(void);

// Functions for extracting a gpi_sim_hdl to an object
// Returns a handle to the root simulation object,
// Should be freed with gpi_free_handle
GPI_EXPORT gpi_sim_hdl gpi_get_root_handle(const char *name);
GPI_EXPORT gpi_sim_hdl gpi_get_handle_by_name(gpi_sim_hdl parent,
                                              const char *name);
GPI_EXPORT gpi_sim_hdl gpi_get_handle_by_index(gpi_sim_hdl parent,
                                               int32_t index);
GPI_EXPORT void gpi_free_handle(gpi_sim_hdl gpi_hdl);

// Types that can be passed to the iterator.
//
// Note these are strikingly similar to the VPI types...
typedef enum gpi_objtype_e {
    GPI_UNKNOWN = 0,
    GPI_MEMORY = 1,
    GPI_MODULE = 2,
    GPI_NET = 3,
    // GPI_PARAMETER = 4,  // Deprecated
    GPI_REGISTER = 5,
    GPI_ARRAY = 6,
    GPI_ENUM = 7,
    GPI_STRUCTURE = 8,
    GPI_REAL = 9,
    GPI_INTEGER = 10,
    GPI_STRING = 11,
    GPI_GENARRAY = 12,
} gpi_objtype_t;

// When iterating, we can chose to either get child objects, drivers or loads
typedef enum gpi_iterator_sel_e {
    GPI_OBJECTS = 1,
    GPI_DRIVERS = 2,
    GPI_LOADS = 3,
} gpi_iterator_sel_t;

typedef enum gpi_set_action_e {
    GPI_DEPOSIT = 0,
    GPI_FORCE = 1,
    GPI_RELEASE = 2,
} gpi_set_action_t;

// Functions for iterating over entries of a handle
// Returns an iterator handle which can then be used in gpi_next calls
//
// Unlike `vpi_iterate` the iterator handle may only be NULL if the `type` is
// not supported, If no objects of the requested type are found, an empty
// iterator is returned.
GPI_EXPORT gpi_iterator_hdl gpi_iterate(gpi_sim_hdl base,
                                        gpi_iterator_sel_t type);

// Returns NULL when there are no more objects
GPI_EXPORT gpi_sim_hdl gpi_next(gpi_iterator_hdl iterator);

// Returns the number of objects in the collection of the handle
GPI_EXPORT int gpi_get_num_elems(gpi_sim_hdl gpi_sim_hdl);

// Returns the left side of the range constraint
GPI_EXPORT int gpi_get_range_left(gpi_sim_hdl gpi_sim_hdl);

// Returns the right side of the range constraint
GPI_EXPORT int gpi_get_range_right(gpi_sim_hdl gpi_sim_hdl);

// Functions for querying the properties of a handle
// Caller responsible for freeing the returned string.
// This is all slightly verbose but it saves having to enumerate various value
// types We only care about a limited subset of values.
GPI_EXPORT const char *gpi_get_signal_value_binstr(gpi_sim_hdl gpi_hdl);
GPI_EXPORT const char *gpi_get_signal_value_str(gpi_sim_hdl gpi_hdl);
GPI_EXPORT double gpi_get_signal_value_real(gpi_sim_hdl gpi_hdl);
GPI_EXPORT long gpi_get_signal_value_long(gpi_sim_hdl gpi_hdl);
GPI_EXPORT const char *gpi_get_signal_name_str(gpi_sim_hdl gpi_hdl);
GPI_EXPORT const char *gpi_get_signal_type_str(gpi_sim_hdl gpi_hdl);

// Returns one of the types defined above e.g. gpiMemory etc.
GPI_EXPORT gpi_objtype_t gpi_get_object_type(gpi_sim_hdl gpi_hdl);

// Get information about the definition of a handle
GPI_EXPORT const char *gpi_get_definition_name(gpi_sim_hdl gpi_hdl);
GPI_EXPORT const char *gpi_get_definition_file(gpi_sim_hdl gpi_hdl);

// Determine whether an object value is constant (parameters / generics etc)
GPI_EXPORT int gpi_is_constant(gpi_sim_hdl gpi_hdl);

// Determine whether an object is indexable
GPI_EXPORT int gpi_is_indexable(gpi_sim_hdl gpi_hdl);

// Functions for setting the properties of a handle
GPI_EXPORT void gpi_set_signal_value_real(gpi_sim_hdl gpi_hdl, double value,
                                          gpi_set_action_t action);
GPI_EXPORT void gpi_set_signal_value_int(gpi_sim_hdl gpi_hdl, int32_t value,
                                         gpi_set_action_t action);
GPI_EXPORT void gpi_set_signal_value_binstr(
    gpi_sim_hdl gpi_hdl, const char *str,
    gpi_set_action_t action);  // String of binary char(s) [1, 0, x, z]
GPI_EXPORT void gpi_set_signal_value_str(
    gpi_sim_hdl gpi_hdl, const char *str,
    gpi_set_action_t action);  // String of ASCII char(s)

typedef enum gpi_edge {
    GPI_RISING = 1,
    GPI_FALLING = 2,
} gpi_edge_e;

// The callback registering functions
GPI_EXPORT gpi_cb_hdl gpi_register_timed_callback(int (*gpi_function)(void *),
                                                  void *gpi_cb_data,
                                                  uint64_t time);
GPI_EXPORT gpi_cb_hdl gpi_register_value_change_callback(
    int (*gpi_function)(void *), void *gpi_cb_data, gpi_sim_hdl gpi_hdl,
    int edge);
GPI_EXPORT gpi_cb_hdl
gpi_register_readonly_callback(int (*gpi_function)(void *), void *gpi_cb_data);
GPI_EXPORT gpi_cb_hdl
gpi_register_nexttime_callback(int (*gpi_function)(void *), void *gpi_cb_data);
GPI_EXPORT gpi_cb_hdl
gpi_register_readwrite_callback(int (*gpi_function)(void *), void *gpi_cb_data);

// Calling convention is that 0 = success and negative numbers a failure
// For implementers of GPI the provided macro GPI_RET(x) is provided
GPI_EXPORT void gpi_deregister_callback(gpi_cb_hdl gpi_hdl);

// Because the internal structures may be different for different
// implementations of GPI we provide a convenience function to extract the
// callback data
GPI_EXPORT void *gpi_get_callback_data(gpi_cb_hdl gpi_hdl);

#ifdef __cplusplus
}
#endif

#endif /* COCOTB_GPI_H_ */
