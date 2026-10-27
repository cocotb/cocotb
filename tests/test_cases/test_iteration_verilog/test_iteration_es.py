# Copyright cocotb contributors
# Copyright (c) 2015, 2018 Potential Ventures Ltd
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import logging

import pytest

import cocotb
from cocotb.handle import ArrayObject, HierarchyArrayObject, HierarchyObject
from cocotb.triggers import gather

SIM_NAME = cocotb.SIM_NAME.lower()


@cocotb.test()
async def recursive_discovery(dut):
    """
    Recursively discover every single object in the design
    """
    pass_total = 26

    # Icarus doesn't support array indexes like get_handle_by_name("some_path[x]")
    SKIP_HANDLE_ASSERT = cocotb.SIM_NAME.lower().startswith(("riviera", "icarus"))

    tlog = logging.getLogger("cocotb.test")

    def sim_iter(parent):
        if not isinstance(
            parent,
            (
                HierarchyObject,
                HierarchyArrayObject,
                ArrayObject,
            ),
        ):
            return
        for thing in parent:
            yield thing
            yield from sim_iter(thing)

    total = 0
    for thing in sim_iter(dut):
        tlog.info("Found %s (%s)", thing._path, type(thing))

        if not SKIP_HANDLE_ASSERT:
            subpath = thing._path.split(".", 1)[1]
            assert dut._handle.get_handle_by_name(subpath) == thing._handle

        total += 1

    tlog.info("Found a total of %d things", total)
    assert total == pass_total


async def iteration_loop(dut):
    for thing in dut:
        cocotb.log.info("Found something: %s", thing._path)


@cocotb.test()
async def dual_iteration(dut):
    loop_one = cocotb.start_soon(iteration_loop(dut))
    loop_two = cocotb.start_soon(iteration_loop(dut))

    await gather(loop_one, loop_two)


@cocotb.test()
async def abandoned_iterator(dut):
    """Dropping a GPI iterator before it is exhausted must free it cleanly.

    Also checks that an exhausted iterator keeps raising StopIteration instead
    of touching the already-freed GPI iterator.
    """
    it = dut._handle.iterate(cocotb.simulator.OBJECTS)
    next(it)
    del it

    # Root iteration is not implemented by every GPI implementation, and on
    # mixed-language simulators the iterator may belong to the implementation
    # that cannot see the toplevel and therefore be empty.
    roots = cocotb.simulator.root_iterate()
    if roots is not None:
        next(roots, None)
        del roots

    it = dut._handle.iterate(cocotb.simulator.OBJECTS)
    count = sum(1 for _ in it)
    assert count > 0
    with pytest.raises(StopIteration):
        next(it)

    # Later discovery still works. (The raw GPI count is not compared: some
    # implementations return the same object through several relationships,
    # which discovery deduplicates.)
    assert sum(1 for _ in dut) > 0
