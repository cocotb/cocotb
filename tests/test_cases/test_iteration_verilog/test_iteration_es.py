# Copyright cocotb contributors
# Copyright (c) 2015, 2018 Potential Ventures Ltd
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import logging

import cocotb
from cocotb.handle import ArrayObject, HierarchyArrayObject, HierarchyObject
from cocotb.triggers import First

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

    await First(loop_one, loop_two)
