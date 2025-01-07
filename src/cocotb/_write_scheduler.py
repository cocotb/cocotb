# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import os
from collections import OrderedDict
from typing import Any, Callable, Sequence, Tuple

import cocotb
import cocotb.handle
import cocotb.task
from cocotb.triggers import ReadOnly, ReadWrite, current_gpi_trigger

trust_inertial = bool(int(os.environ.get("COCOTB_TRUST_INERTIAL_WRITES", "0")))

# A dictionary of pending (write_func, args), keyed by handle.
# Writes are applied oldest to newest (least recently used).
# Only the last scheduled write to a particular handle in a timestep is performed.
_write_calls: "OrderedDict[cocotb.handle.SimHandleBase, Tuple[Callable[..., None], Sequence[Any]]]" = OrderedDict()

_read_only: ReadOnly = ReadOnly()
_read_write: ReadWrite = ReadWrite()


def _write_scheduler_callback() -> None:
    # This function does nothing instead of calling apply_scheduled_writes.
    # apply_scheduled_writes is called by the ReadWrite Trigger's _react to
    # ensure that it occurs first.
    pass


def apply_scheduled_writes() -> None:
    while _write_calls:
        _, (func, args) = _write_calls.popitem(last=False)
        func(*args)


if trust_inertial:

    def schedule_write(
        handle: cocotb.handle.SimHandleBase,
        write_func: Callable[..., None],
        args: Sequence[Any],
    ) -> None:
        if current_gpi_trigger() is _read_only:
            raise RuntimeError(
                f"Write to object {handle._name} was scheduled during a read-only simulation phase."
            )
        write_func(*args)
else:

    def schedule_write(
        handle: cocotb.handle.SimHandleBase,
        write_func: Callable[..., None],
        args: Sequence[Any],
    ) -> None:
        """Queue *write_func* to be called on the next ``ReadWrite`` trigger."""
        current_trigger = current_gpi_trigger()
        if current_trigger is _read_write:
            write_func(*args)
        elif current_trigger is _read_only:
            raise RuntimeError(
                f"Write to object {handle._name} was scheduled during a read-only simulation phase."
            )
        else:
            # This must come first as it checks if _write_calls is empty to see if this is the first scheduling.
            if not _write_calls:
                _read_write.register(_write_scheduler_callback)

            # We explicitly delete so the new handle value doesn't update the old entry without moving it to
            # the end of the queue.
            if handle in _write_calls:
                del _write_calls[handle]
            _write_calls[handle] = (write_func, args)
