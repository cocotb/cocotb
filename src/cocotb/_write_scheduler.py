# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import os
from collections import OrderedDict
from typing import Any, Callable, Dict, Sequence, Tuple, Union

import cocotb
import cocotb.handle
import cocotb.task
from cocotb.triggers import Event, ReadWrite

trust_inertial = bool(int(os.environ.get("COCOTB_TRUST_INERTIAL_WRITES", "0")))

# A dictionary of pending (write_func, args), keyed by handle.
# Writes are applied oldest to newest (least recently used).
# Only the last scheduled write to a particular handle in a timestep is performed.
_write_calls: Dict[
    cocotb.handle.SimHandleBase, Tuple[Callable[..., None], Sequence[Any]]
] = OrderedDict()

# TODO don't use a task to force ReadWrite, just prime an empty callback

_write_task: Union[cocotb.task.Task[None], None] = None

_writes_pending = Event()


async def _do_writes() -> None:
    """An internal task that schedules a ReadWrite to force writes to occur."""
    while True:
        await _writes_pending.wait()
        await ReadWrite()


def start_write_scheduler() -> None:
    global _write_task
    if _write_task is None:
        _write_task = cocotb.start_soon(_do_writes())


def stop_write_scheduler() -> None:
    global _write_task
    if _write_task is not None:
        _write_task.kill()
        _write_task = None
    _write_calls.clear()
    _writes_pending.clear()


def apply_scheduled_writes() -> None:
    while _write_calls:
        _, (func, args) = _write_calls.popitem(last=False)
        func(*args)
    _writes_pending.clear()


if trust_inertial:

    def schedule_write(
        handle: cocotb.handle.SimHandleBase,
        write_func: Callable[..., None],
        args: Sequence[Any],
    ) -> None:
        write_func(*args)
else:

    def schedule_write(
        handle: cocotb.handle.SimHandleBase,
        write_func: Callable[..., None],
        args: Sequence[Any],
    ) -> None:
        """Queue *write_func* to be called on the next ``ReadWrite`` trigger."""
        if cocotb.sim_phase == cocotb.SimPhase.READ_WRITE:
            write_func(*args)
        elif cocotb.sim_phase == cocotb.SimPhase.READ_ONLY:
            raise RuntimeError(
                f"Write to object {handle._name} was scheduled during a read-only sync phase."
            )
        else:
            if handle in _write_calls:
                del _write_calls[handle]
            _write_calls[handle] = (write_func, args)
            _writes_pending.set()
