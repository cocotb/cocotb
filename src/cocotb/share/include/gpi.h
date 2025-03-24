// Copyright cocotb contributors
// Copyright (c) 2013, 2018 Potential Ventures Ltd
// Copyright (c) 2013 SolarFlare Communications Inc
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#ifndef COCOTB_GPI_H_
#define COCOTB_GPI_H_

/** \file gpi.h

Generic Language Interface
==========================

This header file defines a Generic Language Interface into any simulator.
Implementations need to implement the underlying functions in `gpi_priv.h`.

The functions are essentially a limited subset of VPI/VHPI/FLI.

Implementation-specific notes
-----------------------------

By amazing coincidence, VPI and VHPI are strikingly similar which is obviously
reflected by this header file. Unfortunately, this means that proprietary,
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

// Forward declaration for types needed in function signatures
typedef enum gpi_discovery_e {
    GPI_AUTO = 0,
    GPI_NATIVE = 1,
} gpi_discovery;

// Functions for controlling/querying the simulation state

/**
 * Return if there is a registered GPI implementation.
 * Useful for checking if a simulator is running.
 *
 * @return `1` if there is a registered GPI implementation, `0` otherwise.
 */
GPI_EXPORT bool gpi_has_registered_impl(void);

/**
 * Stop the simulator.
 */
GPI_EXPORT void gpi_sim_end(void);

/**
 * Return simulation time as two uints. Unit is the default sim unit.
 */
GPI_EXPORT void gpi_get_sim_time(uint32_t *high, uint32_t *low);
GPI_EXPORT void gpi_get_sim_precision(int32_t *precision);

/**
 * Return a string with the running simulator product information.
 *
 * @return The simulator product string.
 */
GPI_EXPORT const char *gpi_get_simulator_product(void);

/**
 * Return a string with the running simulator version.
 *
 * @return The simulator version string.
 */
GPI_EXPORT const char *gpi_get_simulator_version(void);

// Functions for extracting a gpi_sim_hdl to an object

/**
 * Returns a handle to the root simulation object.
 */
GPI_EXPORT gpi_sim_hdl gpi_get_root_handle(const char *name);
GPI_EXPORT gpi_sim_hdl gpi_get_handle_by_name(gpi_sim_hdl parent,
                                              const char *name,
                                              gpi_discovery discovery_method);
GPI_EXPORT gpi_sim_hdl gpi_get_handle_by_index(gpi_sim_hdl parent,
                                               int32_t index);

/**
 * Types that can be passed to the iterator.
 */
// Note these are strikingly similar to the VPI types...
typedef enum gpi_objtype_e {
    GPI_UNKNOWN = 0,
    GPI_MEMORY = 1,
    GPI_MODULE = 2,
    // GPI_NET = 3,  // Deprecated
    // GPI_PARAMETER = 4,  // Deprecated
    // GPI_REGISTER = 5,  // Deprecated
    GPI_ARRAY = 6,
    GPI_ENUM = 7,
    GPI_STRUCTURE = 8,
    GPI_REAL = 9,
    GPI_INTEGER = 10,
    GPI_STRING = 11,
    GPI_GENARRAY = 12,
    GPI_PACKAGE = 13,
    GPI_PACKED_STRUCTURE = 14,
    GPI_LOGIC = 15,
    GPI_LOGIC_ARRAY = 16,
} gpi_objtype;

/**
 * When iterating, we can chose to either get child objects, drivers or loads.
 */
typedef enum gpi_iterator_sel_e {
    GPI_OBJECTS = 1,
    GPI_DRIVERS = 2,
    GPI_LOADS = 3,
    GPI_PACKAGE_SCOPES = 4,
} gpi_iterator_sel;

typedef enum gpi_set_action_e {
    GPI_DEPOSIT = 0,
    GPI_FORCE = 1,
    GPI_RELEASE = 2,
    GPI_NO_DELAY = 3,
} gpi_set_action;

typedef enum gpi_range_dir_e {
    GPI_RANGE_DOWN = -1,
    GPI_RANGE_NO_DIR = 0,
    GPI_RANGE_UP = 1,
} gpi_range_dir;

typedef enum gpi_edge_e {
    GPI_RISING,
    GPI_FALLING,
    GPI_VALUE_CHANGE,
} gpi_edge;

// Functions for iterating over entries of a handle

/**
 * Return an iterator handle which can then be used in `gpi_next` calls.
 *
 * Unlike `vpi_iterate` the iterator handle may only be `NULL` if the `type` is
 * not supported, If no objects of the requested type are found, an empty
 * iterator is returned.
 */
GPI_EXPORT gpi_iterator_hdl gpi_iterate(gpi_sim_hdl base,
                                        gpi_iterator_sel type);

/**
 * @return `NULL` when there are no more objects.
 */
GPI_EXPORT gpi_sim_hdl gpi_next(gpi_iterator_hdl iterator);

/**
 * @return The number of objects in the collection of the handle.
 */
GPI_EXPORT int gpi_get_num_elems(gpi_sim_hdl gpi_sim_hdl);

/**
 * @return The left side of the range constraint.
 */
GPI_EXPORT int gpi_get_range_left(gpi_sim_hdl gpi_sim_hdl);

/**
 * @return The right side of the range constraint.
 */
GPI_EXPORT int gpi_get_range_right(gpi_sim_hdl gpi_sim_hdl);

/**
 * @return The direction of the range constraint:
 *         `+1` for ascending, `-1` for descending, `0` for undefined.
 */
GPI_EXPORT gpi_range_dir gpi_get_range_dir(gpi_sim_hdl gpi_sim_hdl);

// Functions for querying the properties of a handle

/**
 * This is all slightly verbose but it saves having to enumerate various value
 * types. We only care about a limited subset of values.
 */
GPI_EXPORT const char *gpi_get_signal_value_binstr(gpi_sim_hdl gpi_hdl);
GPI_EXPORT const char *gpi_get_signal_value_str(gpi_sim_hdl gpi_hdl);
GPI_EXPORT double gpi_get_signal_value_real(gpi_sim_hdl gpi_hdl);
GPI_EXPORT long gpi_get_signal_value_long(gpi_sim_hdl gpi_hdl);
GPI_EXPORT const char *gpi_get_signal_name_str(gpi_sim_hdl gpi_hdl);
GPI_EXPORT const char *gpi_get_signal_type_str(gpi_sim_hdl gpi_hdl);

/**
 * @return One of the types defined above.
 */
GPI_EXPORT gpi_objtype gpi_get_object_type(gpi_sim_hdl gpi_hdl);

/**
 * Get information about the definition of a handle.
 */
GPI_EXPORT const char *gpi_get_definition_name(gpi_sim_hdl gpi_hdl);
GPI_EXPORT const char *gpi_get_definition_file(gpi_sim_hdl gpi_hdl);

/**
 * Determine whether an object value is constant (parameters / generics etc).
 */
GPI_EXPORT int gpi_is_constant(gpi_sim_hdl gpi_hdl);

/**
 * Determine whether an object is indexable.
 */
GPI_EXPORT int gpi_is_indexable(gpi_sim_hdl gpi_hdl);

// Functions for setting the properties of a handle

GPI_EXPORT void gpi_set_signal_value_real(gpi_sim_hdl gpi_hdl, double value,
                                          gpi_set_action action);
GPI_EXPORT void gpi_set_signal_value_int(gpi_sim_hdl gpi_hdl, int32_t value,
                                         gpi_set_action action);
GPI_EXPORT void gpi_set_signal_value_binstr(
    gpi_sim_hdl gpi_hdl, const char *str,
    gpi_set_action action);  // String of binary char(s) [1, 0, x, z]
GPI_EXPORT void gpi_set_signal_value_str(
    gpi_sim_hdl gpi_hdl, const char *str,
    gpi_set_action action);  // String of ASCII char(s)

// The callback registering functions

GPI_EXPORT gpi_cb_hdl gpi_register_timed_callback(int (*gpi_function)(void *),
                                                  void *gpi_cb_data,
                                                  uint64_t time);
GPI_EXPORT gpi_cb_hdl gpi_register_value_change_callback(
    int (*gpi_function)(void *), void *gpi_cb_data, gpi_sim_hdl gpi_hdl,
    gpi_edge edge);
GPI_EXPORT gpi_cb_hdl
gpi_register_readonly_callback(int (*gpi_function)(void *), void *gpi_cb_data);
GPI_EXPORT gpi_cb_hdl
gpi_register_nexttime_callback(int (*gpi_function)(void *), void *gpi_cb_data);
GPI_EXPORT gpi_cb_hdl
gpi_register_readwrite_callback(int (*gpi_function)(void *), void *gpi_cb_data);

/** Remove callback.
 *
 * The callback will not fire after this function is called.
 * The argument is no longer valid if this function succeeds.
 *
 * @param cb_hdl The handle to the callback to remove.
 * @returns `0` on successful removal, `1` otherwise.
 */
GPI_EXPORT int gpi_remove_cb(gpi_cb_hdl cb_hdl);

/** Retrieve user callback information from callback handle.
 *
 * This function cannot fail.
 *
 * @param cb_hdl The handle to the callback.
 * @param cb_func Where the user callback function should be placed.
 * @param cb_data Where the user callback function data should be placed.
 */
GPI_EXPORT void gpi_get_cb_info(gpi_cb_hdl cb_hdl, int (**cb_func)(void *),
                                void **cb_data);

#ifdef __cplusplus
}
#endif

#endif /* COCOTB_GPI_H_ */
