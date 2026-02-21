# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""Monkey-patch installer for Cython hot-path accelerators.

Imports optimized functions from :mod:`cocotb._fast` and patches them
into the appropriate classes.  Disabled by setting the environment
variable ``COCOTB_DISABLE_FAST=1``.

This module is safe to import even if the Cython extension was not
compiled — it simply logs a message and returns.
"""

from __future__ import annotations

import logging
import os
from typing import Any

_log = logging.getLogger(__name__)

_installed = False


def install() -> None:
    """Install Cython fast-path replacements into cocotb classes.

    This is idempotent — calling it multiple times has no effect after
    the first successful installation.
    """
    global _installed
    if _installed:
        return

    if os.environ.get("COCOTB_DISABLE_FAST", "0") == "1":
        _log.info("Cython fast paths disabled via COCOTB_DISABLE_FAST=1")
        _installed = True
        return

    try:
        from cocotb import _fast  # type: ignore[attr-defined]
    except ImportError:
        _log.debug(
            "cocotb._fast Cython extension not available; using pure-Python hot paths"
        )
        _installed = True
        return

    _patch_logic_array_from_handle(_fast)
    _patch_hierarchy_getattr(_fast)
    _patch_cached_len()
    _patch_logic_object_get(_fast)
    _patch_enum_cache()
    _patch_value_setter()
    _patch_schedule_write()
    _patch_event_loop()

    _installed = True
    _log.debug("Cython fast paths installed successfully")


def _patch_logic_array_from_handle(fast_mod: object) -> None:
    """Replace LogicArray._from_handle with the Cython-cached version."""
    from cocotb.types._logic_array import LogicArray

    @classmethod  # type: ignore[misc]
    def _from_handle(
        cls: type[LogicArray], value: str, warn_indexing: bool
    ) -> LogicArray:
        return fast_mod.fast_logic_array_from_handle(cls, value, warn_indexing)  # type: ignore[attr-defined]

    LogicArray._from_handle = _from_handle  # type: ignore[method-assign,assignment]
    _log.debug("Patched LogicArray._from_handle")


def _patch_hierarchy_getattr(fast_mod: object) -> None:
    """Replace HierarchyObject.__getattr__ with the fast C-level version."""
    from cocotb.handle import HierarchyObject

    HierarchyObject.__getattr__ = fast_mod.fast_getattr  # type: ignore[attr-defined,method-assign]
    _log.debug("Patched HierarchyObject.__getattr__")


def _patch_cached_len() -> None:
    """Cache LogicArrayObject.__len__ result.

    Signal widths are constant per handle, but the current implementation
    calls into the GPI layer (``self._handle.get_num_elems()``) on every
    ``len()`` call.  This patch caches the result on first call.
    """
    from cocotb.handle import LogicArrayObject

    original_len = LogicArrayObject.__len__

    def _cached_len(self: Any) -> int:
        try:
            return self.__dict__["_cached_num_elems"]
        except KeyError:
            result = original_len(self)
            self.__dict__["_cached_num_elems"] = result
            return result

    LogicArrayObject.__len__ = _cached_len  # type: ignore[method-assign]
    _log.debug("Patched LogicArrayObject.__len__ with caching")


def _patch_logic_object_get(fast_mod: object) -> None:
    """Replace LogicObject.get() with a version using the fast char lookup."""
    from cocotb.handle import LogicObject

    def _fast_get(self: Any) -> Any:
        binstr = self._handle.get_signal_val_binstr()
        return fast_mod.fast_logic_from_char(binstr)  # type: ignore[attr-defined]

    LogicObject.get = _fast_get  # type: ignore[method-assign]
    _log.debug("Patched LogicObject.get()")


def _patch_enum_cache() -> None:
    """Cache _GPISetAction enum .value accesses as module-level constants.

    Accessing ``_GPISetAction.DEPOSIT.value`` on every write goes through
    the enum descriptor protocol.  We cache the integer values once.
    """
    from cocotb import handle as _handle_mod

    # Cache the integer values
    _handle_mod._DEPOSIT_INT = _handle_mod._GPISetAction.DEPOSIT.value  # type: ignore[attr-defined]
    _handle_mod._DEPOSIT_ACTION = _handle_mod._GPISetAction.DEPOSIT  # type: ignore[attr-defined]
    _log.debug("Cached _GPISetAction enum values")


def _patch_value_setter() -> None:
    """Optimize ValueObjectBase.value setter to reduce per-call overhead.

    - Caches the ReadOnly type check using a cached type reference
    - Uses cached _Action type reference instead of per-call import
    - Uses cached _GPISetAction.DEPOSIT instead of enum lookup
    """
    from cocotb._gpi_triggers import ReadOnly, current_gpi_trigger
    from cocotb.handle import ValueObjectBase, _Action, _GPISetAction

    _deposit = _GPISetAction.DEPOSIT
    # Pre-build a set of _Action subclass types for O(1) lookup
    _action_types = frozenset({_Action} | set(_Action.__subclasses__()))

    def _fast_value_setter(
        self: Any,
        value: Any,
    ) -> None:
        if current_gpi_trigger().__class__ is ReadOnly:
            raise RuntimeError("Attempting settings a value during the ReadOnly phase.")
        if self.is_const:
            raise TypeError("Attempted setting an immutable object")
        if type(value) in _action_types:
            return value._dispatch(self)
        return self._set_value(value, _deposit)

    original_prop = ValueObjectBase.__dict__["value"]
    new_prop = original_prop.setter(_fast_value_setter)
    ValueObjectBase.value = new_prop  # type: ignore[method-assign]
    _log.debug("Patched ValueObjectBase.value setter")


def _patch_schedule_write() -> None:
    """Optimize _schedule_write to use cached enum int values.

    Replaces action.value (enum descriptor) with pre-cached integer.
    """
    from cocotb import handle as _handle_mod
    from cocotb._gpi_triggers import ReadWrite, current_gpi_trigger
    from cocotb.handle import _GPISetAction

    _trust_inertial = _handle_mod._trust_inertial

    if _trust_inertial:
        _deposit_int = _GPISetAction.DEPOSIT.value

        def _fast_schedule_write(
            handle: Any, write_func: Any, action: Any, value: Any
        ) -> None:
            write_func(
                action.value if action is not _GPISetAction.DEPOSIT else _deposit_int,
                value,
            )

        _handle_mod._schedule_write = _fast_schedule_write
        _log.debug("Patched _schedule_write (trust_inertial mode)")
    else:
        _deposit_int = _GPISetAction.DEPOSIT.value
        _deposit_action = _GPISetAction.DEPOSIT

        def _fast_schedule_write_queued(
            handle: Any, write_func: Any, action: Any, value: Any
        ) -> None:
            if current_gpi_trigger().__class__ is ReadWrite:
                write_func(
                    _deposit_int if action is _deposit_action else action.value,
                    value,
                )
            elif action is _deposit_action:
                write_calls = _handle_mod._write_calls
                if handle in write_calls:
                    del write_calls[handle]
                write_calls[handle] = (write_func, action, value)

                if _handle_mod._apply_writes_cb is None:
                    _handle_mod._apply_writes_cb = ReadWrite()._register(lambda: None)
            else:
                write_func(action.value, value)

        _handle_mod._schedule_write = _fast_schedule_write_queued
        _log.debug("Patched _schedule_write (queued mode)")


def _patch_event_loop() -> None:
    """Optimize EventLoop.run() to reduce per-callback overhead.

    The hot inner loop checks debug.debug on every iteration and calls
    cb._run() which is just cb._func(). We replace with a tighter loop
    that skips debug checks in the common non-debug case.
    """
    from cocotb import debug
    from cocotb._bridge import run_bridge_threads
    from cocotb._event_loop import EventLoop

    def _fast_run(self: Any) -> None:
        callbacks = self._callbacks
        self._cycles = 0
        while callbacks:
            while callbacks:
                cb = callbacks.popleft()
                if not cb._cancelled:
                    cb._func()
            run_bridge_threads()

    def _fast_run_debug(self: Any) -> None:
        # Fallback with debug support — identical to original
        callbacks = self._callbacks
        self._cycles = 0
        while callbacks:
            while callbacks:
                cb = callbacks.popleft()
                if not cb._cancelled:
                    self.log.debug("Running callback %r", cb)
                    cb._func()
                else:
                    self.log.debug("Ignoring cancelled callback %r", cb)
                self._cycles += 1
                if self._cycles == 100_000:
                    self.log.warning(
                        "Event loop ran 100,000 cycles without returning. "
                        "An infinite loop is possible."
                    )
                    self._cycles = 0
            run_bridge_threads()

    if debug.debug:
        EventLoop.run = _fast_run_debug  # type: ignore[method-assign]
    else:
        EventLoop.run = _fast_run  # type: ignore[method-assign]

    _log.debug("Patched EventLoop.run()")
