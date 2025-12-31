# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import gc
import weakref
from collections.abc import Callable
from pathlib import Path

from cocotb import simulator


def record(message: str) -> None:
    with Path("results.log").open("a") as file:
        print(message, file=file)


def register_callback() -> tuple[
    simulator.sim_callback, weakref.ReferenceType[Callable[[], None]]
]:
    def callback() -> None:
        record("cancelled")

    handle = simulator.register_end_of_sim_time_callback(callback)
    assert handle is not None
    return handle, weakref.ref(callback)


def entry_func() -> None:
    handle, ref = register_callback()
    handle.deregister()

    # Check for leak of callback reference after deregistration
    gc.collect()
    assert ref() is None, "callback should have been released"

    a = simulator.register_end_of_sim_time_callback(record, "cancelled")
    _ = simulator.register_end_of_sim_time_callback(record, "retained 1")
    c = simulator.register_end_of_sim_time_callback(record, "cancelled")
    _ = simulator.register_end_of_sim_time_callback(record, "retained 2")

    a.deregister()
    c.deregister()

    # Log file will contain only "retained 1" and "retained 2" in that order
    # since the callbacks are executed in order of registration.
