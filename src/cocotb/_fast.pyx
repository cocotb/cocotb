# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
#
# Cython hot-path accelerators for cocotb.
# This module provides optimized replacements for the most expensive
# Python-level operations in cocotb's signal read/write path.

from cpython.dict cimport PyDict_GetItem
from cpython.object cimport PyObject

# ---------------------------------------------------------------------------
# 1. Range cache — eliminate repeated Range allocations for the same width
# ---------------------------------------------------------------------------

# Cache of Range objects keyed by signal width (int).
# Signal widths are constant per handle, so this is safe to cache globally.
cdef dict _range_cache = {}


def fast_logic_array_from_handle(cls, str value, bint warn_indexing):
    """Optimized replacement for LogicArray._from_handle.

    Caches Range objects by signal width so we don't allocate a new Range
    for every read of the same-width signal.
    """
    cdef int width = len(value)
    cdef object range_obj

    # Fast dict lookup without exception overhead
    cdef PyObject* cached = PyDict_GetItem(_range_cache, width)
    if cached != NULL:
        range_obj = <object>cached
    else:
        from cocotb.types import Range
        range_obj = Range(width - 1, "downto", 0)
        _range_cache[width] = range_obj

    # Directly construct LogicArray bypassing __init__
    cdef object self = cls.__new__(cls)
    self._value_as_array = None
    self._value_as_int = None
    self._value_as_str = value
    self._range = range_obj
    self._warn_indexing = warn_indexing
    return self


# ---------------------------------------------------------------------------
# 2. Logic char cache — bypass Logic.__new__ isinstance chains
# ---------------------------------------------------------------------------

# Lookup table: ASCII ordinal -> cached Logic singleton (or None)
# Populated on first use from Logic's _literal_repr table.
cdef list _logic_char_table = []
cdef bint _logic_char_table_ready = 0


cdef _init_logic_char_table():
    """Build the ASCII -> Logic lookup table from Logic._literal_repr."""
    global _logic_char_table, _logic_char_table_ready
    from cocotb.types._logic import Logic, _literal_repr

    # 256-entry table covering all ASCII values; None for invalid chars
    _logic_char_table = [None] * 256

    # Pre-populate for all single-character string keys in _literal_repr
    for key, repr_val in _literal_repr.items():
        if isinstance(key, str) and len(key) == 1:
            singleton = Logic._singleton(repr_val)
            _logic_char_table[ord(key)] = singleton
        elif isinstance(key, int) and 0 <= key <= 1:
            # Integer keys 0, 1 — also map the ASCII digits
            singleton = Logic._singleton(repr_val)
            _logic_char_table[ord(str(key))] = singleton

    _logic_char_table_ready = 1


def fast_logic_from_char(str c):
    """Optimized replacement for Logic(single_char_binstr).

    Uses a pre-built C-level lookup table mapping ASCII char ordinals
    to cached Logic singletons.  Bypasses Logic.__new__'s isinstance
    chains and dict lookups.
    """
    if not _logic_char_table_ready:
        _init_logic_char_table()

    cdef int ordinal = ord(c)
    if ordinal < 256:
        result = _logic_char_table[ordinal]
        if result is not None:
            return result

    # Fallback to normal constructor for unexpected values
    from cocotb.types import Logic
    return Logic(c)


# ---------------------------------------------------------------------------
# 3. Fast __getattr__ for HierarchyObject
# ---------------------------------------------------------------------------

def fast_getattr(self, str name):
    """Optimized replacement for HierarchyObject.__getattr__.

    Uses PyDict_GetItem (no exception on miss) and C-level string
    prefix check instead of str.startswith.
    """
    # C-level check for underscore prefix
    if len(name) > 0 and name[0] == '_':
        return object.__getattribute__(self, name)

    # Try the _sub_handles cache first using PyDict_GetItem (no KeyError)
    cdef dict sub_handles = self._sub_handles
    cdef PyObject* cached = PyDict_GetItem(sub_handles, name)
    if cached != NULL:
        return <object>cached

    # Cache miss — go through the full _get path which handles GPI lookup
    handle = self._get(name)
    if handle is None:
        raise AttributeError(
            f"{self._path} contains no child object named {name}"
        )
    return handle


# ---------------------------------------------------------------------------
# 4. Fast value setter for common deposit case
# ---------------------------------------------------------------------------

def fast_value_setter(self, value):
    """Optimized value setter for the common case.

    Combines the value.setter -> _set_value -> _schedule_write path
    for the most common case: depositing a raw int, str, Logic,
    or LogicArray value (not an Action like Deposit/Force/Freeze/Release).

    Skips isinstance(_Action) check by duck-typing: if value doesn't
    have _dispatch, it's a raw value.
    """
    # Check ReadOnly phase (still required for correctness)
    from cocotb._gpi_triggers import ReadOnly, current_gpi_trigger
    if isinstance(current_gpi_trigger(), ReadOnly):
        raise RuntimeError(
            "Attempting settings a value during the ReadOnly phase."
        )

    # Check const (cached_property, so this is a dict lookup after first call)
    if self.is_const:
        raise TypeError("Attempted setting an immutable object")

    # Duck-type check for _Action subclasses
    dispatch = getattr(value, '_dispatch', None)
    if dispatch is not None:
        return dispatch(self)

    # Fast path: direct deposit
    from cocotb.handle import _GPISetAction
    return self._set_value(value, _GPISetAction.DEPOSIT)
