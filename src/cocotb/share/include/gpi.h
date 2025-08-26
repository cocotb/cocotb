// Copyright cocotb contributors
// Copyright (c) 2013, 2018 Potential Ventures Ltd
// Copyright (c) 2013 SolarFlare Communications Inc
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#ifndef COCOTB_GPI_H_
#define COCOTB_GPI_H_

/** @file gpi.h

Generic Procedural Interface
============================

This header file defines the GPI to interface with any simulator that supports
VPI, VHPI, or FLI.

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

/** Object discovery method when searching by name. */
typedef enum gpi_discovery_e {
    GPI_AUTO = 0,
    GPI_NATIVE = 1,
} gpi_discovery;

/** GPI simulation object types. */
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

/** Types of child objects to search for when iterating. */
typedef enum gpi_iterator_sel_e {
    GPI_OBJECTS = 1,
    GPI_DRIVERS = 2,
    GPI_LOADS = 3,
    GPI_PACKAGE_SCOPES = 4,
} gpi_iterator_sel;

/** Action to use when setting object value. */
typedef enum gpi_set_action_e {
    GPI_DEPOSIT = 0,
    GPI_FORCE = 1,
    GPI_RELEASE = 2,
    GPI_NO_DELAY = 3,
} gpi_set_action;

/** Direction of range constraint of an object. */
typedef enum gpi_range_dir_e {
    GPI_RANGE_DOWN = -1,
    GPI_RANGE_NO_DIR = 0,
    GPI_RANGE_UP = 1,
} gpi_range_dir;

/** Type of value change to match when registering for callback. */
typedef enum gpi_edge_e {
    GPI_RISING,
    GPI_FALLING,
    GPI_VALUE_CHANGE,
} gpi_edge;

/** @defgroup SimIntf Simulator Control and Interrogation
 * These functions are for controlling and querying
 * simulator state and information.
 * @{
 */

/** Check if there is a registered GPI implementation.
 *
 * Useful for checking if a simulator is running.
 *
 * @return `1` if there is a registered GPI implementation, `0` otherwise.
 */
GPI_EXPORT bool gpi_has_registered_impl(void);

/** Stop the simulation after control returns to the GPI. */
GPI_EXPORT void gpi_sim_end(void);

/** Get the simulation time as two 32-bit uints.
 *
 * The value is in default simulation time units,
 * which can be retrieved with @ref gpi_get_sim_precision.
 *
 * @param high  Location to return high bits of current simulation time.
 * @param low   Location to return low bits of current simulation time.
 */
GPI_EXPORT void gpi_get_sim_time(uint32_t *high, uint32_t *low);

/** Get the simulation time precision.
 *
 * @param precision  Location to return time precision.
 *                   The value is scientific notation in terms of seconds.
 *                   So a value of `-9` is nanosecond precision.
 */
GPI_EXPORT void gpi_get_sim_precision(int32_t *precision);

/** Get the running simulator product information.
 *
 * @return The simulator product string.
 */
GPI_EXPORT const char *gpi_get_simulator_product(void);

/** Get the running simulator version string.
 *
 * @return The simulator version string.
 */
GPI_EXPORT const char *gpi_get_simulator_version(void);

/** @} */  // End of group SimIntf

/** @defgroup ObjQuery Simulation Object Query
 * These functions are for getting handles to simulation objects.
 * @{
 */

/** Get a handle to the root simulation object.
 *
 * @param name  Name of the root object, or `NULL`.
 * @return      Handle to simulation object or `NULL` if not found.
 */
GPI_EXPORT gpi_sim_hdl gpi_get_root_handle(const char *name);

/** Get a handle to a child simulation object by its name.
 *
 * @param parent            Parent object handle.
 * @param name              Name of the child object.
 *                          This should not be a path,
 *                          but only the name of a direct child object.
 * @param discovery_method  Object discovery method.
 * @return                  Handle to simulation object or `NULL` if not found.
 */
GPI_EXPORT gpi_sim_hdl gpi_get_handle_by_name(gpi_sim_hdl parent,
                                              const char *name,
                                              gpi_discovery discovery_method);

/** Get a handle to a child simulation object by its index.
 *
 * @param parent    Parent indexable object handle.
 * @param index     Index of the child object.
 * @return          Handle to simulation object or `NULL` if not found.
 */
GPI_EXPORT gpi_sim_hdl gpi_get_handle_by_index(gpi_sim_hdl parent,
                                               int32_t index);

/** @} */  // End of group ObjQuery

/** @defgroup ObjProps General Object Properties
 * These functions are for getting and setting properties of a simulation
 * object.
 * @{
 */

/** @return The @ref gpi_objtype "type" of the simulation object. */
GPI_EXPORT gpi_objtype gpi_get_object_type(gpi_sim_hdl gpi_hdl);

/** @return Definition name of the simulation object. */
GPI_EXPORT const char *gpi_get_definition_name(gpi_sim_hdl gpi_hdl);

/** @return Definition file of the simulation object. */
GPI_EXPORT const char *gpi_get_definition_file(gpi_sim_hdl gpi_hdl);

/** @return The number of objects in the collection of the handle. */
GPI_EXPORT int gpi_get_num_elems(gpi_sim_hdl gpi_sim_hdl);

/** @return The left side of the range constraint. */
GPI_EXPORT int gpi_get_range_left(gpi_sim_hdl gpi_sim_hdl);

/** @return The right side of the range constraint. */
GPI_EXPORT int gpi_get_range_right(gpi_sim_hdl gpi_sim_hdl);

/** @return The direction of the range constraint:
 *         `+1` for ascending, `-1` for descending, `0` for undefined.
 */
GPI_EXPORT gpi_range_dir gpi_get_range_dir(gpi_sim_hdl gpi_sim_hdl);

/** Determine whether an object value is constant (parameters / generics etc).
 *
 * @return `1` if the object value is constant, `0` otherwise.
 */
GPI_EXPORT int gpi_is_constant(gpi_sim_hdl gpi_hdl);

/** Determine whether an object is indexable.
 *
 * @return `1` if the object value is indexable, `0` otherwise.
 */
GPI_EXPORT int gpi_is_indexable(gpi_sim_hdl gpi_hdl);

/** @} */  // End of group ObjProps

/** @defgroup SigProps Signal Object Properties
 * These functions are for getting and setting properties of a signal object.
 * @{
 */

// Getting properties

/** Get signal object value as a binary string.
 * @param gpi_hdl   Signal object handle.
 * @return          Object value.
 */
GPI_EXPORT const char *gpi_get_signal_value_binstr(gpi_sim_hdl gpi_hdl);

/** Get signal object value as a byte array.
 * @param gpi_hdl   Signal object handle.
 * @return          Object value. Null-terminated byte array.
 */
GPI_EXPORT const char *gpi_get_signal_value_str(gpi_sim_hdl gpi_hdl);

/** Get signal object value as a real.
 * @param gpi_hdl   Signal object handle.
 * @return          Object value.
 */
GPI_EXPORT double gpi_get_signal_value_real(gpi_sim_hdl gpi_hdl);

/** Get signal object value as a long.
 * @param gpi_hdl   Signal object handle.
 * @return          Object value.
 */
GPI_EXPORT long gpi_get_signal_value_long(gpi_sim_hdl gpi_hdl);

/** Get signal object name.
 * @param gpi_hdl   Signal object handle.
 * @return          Object name.
 */
GPI_EXPORT const char *gpi_get_signal_name_str(gpi_sim_hdl gpi_hdl);

/** Get signal object type as a string.
 * @param gpi_hdl   Signal object handle.
 * @return          Object type as a string.
 */
GPI_EXPORT const char *gpi_get_signal_type_str(gpi_sim_hdl gpi_hdl);

// Setting properties

/** Set signal object value with a real.
 * @param gpi_hdl   Signal object handle.
 * @param value     Object value.
 * @param action    Action to use.
 */
GPI_EXPORT void gpi_set_signal_value_real(gpi_sim_hdl gpi_hdl, double value,
                                          gpi_set_action action);

/** Set signal object value with an int.
 * @param gpi_hdl   Signal object handle.
 * @param value     Object value.
 * @param action    Action to use.
 */
GPI_EXPORT void gpi_set_signal_value_int(gpi_sim_hdl gpi_hdl, int32_t value,
                                         gpi_set_action action);

/** Set signal object value with a binary string.
 * @param gpi_hdl   Signal object handle.
 * @param str       Object value. Null-terminated string of binary characters
 *                  in [`1`, `0`, `x`, `z`].
 * @param action    Action to use.
 */
GPI_EXPORT void gpi_set_signal_value_binstr(gpi_sim_hdl gpi_hdl,
                                            const char *str,
                                            gpi_set_action action);

/** Set signal object value with a byte array.
 * @param gpi_hdl   Signal object handle.
 * @param str       Object value. Null-terminated byte array.
 * @param action    Action to use.
 */
GPI_EXPORT void gpi_set_signal_value_str(gpi_sim_hdl gpi_hdl, const char *str,
                                         gpi_set_action action);

/** @} */  // End of group SigProps

/** @defgroup HandleIteration Simulation Object Iteration
 * These functions are for iterating over simulation object handles
 * to discover child objects.
 * @{
 */

/** Start iteration on a simulation object.
 *
 * Unlike `vpi_iterate()` the iterator handle may only be `NULL` if the `type`
 * is not supported. If no objects of the requested type are found, an empty
 * iterator is returned.
 * @param base  Simulation object to iterate over.
 * @param type  Iteration type.
 * @return      An iterator handle which can then be used with @ref gpi_next.
 */
GPI_EXPORT gpi_iterator_hdl gpi_iterate(gpi_sim_hdl base,
                                        gpi_iterator_sel type);

/** Get next object in iteration.
 *
 * @param iterator  Iterator handle.
 * @return          Object handle, or `NULL` when there are no more objects.
 */
GPI_EXPORT gpi_sim_hdl gpi_next(gpi_iterator_hdl iterator);

/** @} */  // End of group HandleIteration

/** @defgroup SimCallbacks Simulation Callbacks
 * These functions are for registering and controlling callbacks.
 * @{
 */

/** Register a timed callback.
 *
 * @param gpi_function  Callback function pointer.
 * @param gpi_cb_data   Pointer to user data to be passed to callback function.
 * @param time          Time delay in simulation time units.
 * @return              Handle to callback object.
 */
GPI_EXPORT gpi_cb_hdl gpi_register_timed_callback(int (*gpi_function)(void *),
                                                  void *gpi_cb_data,
                                                  uint64_t time);

/** Register a value change callback.
 *
 * @param gpi_function  Callback function pointer.
 * @param gpi_cb_data   Pointer to user data to be passed to callback function.
 * @param gpi_hdl       Simulation object to monitor for value change.
 * @param edge          Type of value change to monitor for.
 * @return              Handle to callback object.
 */
GPI_EXPORT gpi_cb_hdl gpi_register_value_change_callback(
    int (*gpi_function)(void *), void *gpi_cb_data, gpi_sim_hdl gpi_hdl,
    gpi_edge edge);

/** Register a readonly simulation phase callback.
 *
 * Callback will be called when simulation next enters the readonly phase.
 * @param gpi_function  Callback function pointer.
 * @param gpi_cb_data   Pointer to user data to be passed to callback function.
 * @return              Handle to callback object.
 */
GPI_EXPORT gpi_cb_hdl
gpi_register_readonly_callback(int (*gpi_function)(void *), void *gpi_cb_data);

/** Register a next timestep simulation phase callback.
 *
 * Callback will be called when simulation next enters the next timestep.
 * @param gpi_function  Callback function pointer.
 * @param gpi_cb_data   Pointer to user data to be passed to callback function.
 * @return              Handle to callback object.
 */
GPI_EXPORT gpi_cb_hdl
gpi_register_nexttime_callback(int (*gpi_function)(void *), void *gpi_cb_data);

/** Register a readwrite simulation phase callback.
 *
 * Callback will be called when simulation next enters the readwrite phase.
 * @param gpi_function  Callback function pointer.
 * @param gpi_cb_data   Pointer to user data to be passed to callback function.
 * @return              Handle to callback object.
 */
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

/** @} */  // End of group SimCallbacks

#ifdef __cplusplus
}
#endif

#endif /* COCOTB_GPI_H_ */
