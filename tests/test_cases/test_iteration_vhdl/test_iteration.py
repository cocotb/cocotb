# Copyright cocotb contributors
# Copyright (c) 2015, 2018 Potential Ventures Ltd
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import logging
import os

import cocotb
from cocotb.handle import ArrayObject, HierarchyArrayObject, HierarchyObject
from cocotb.triggers import Combine, Timer


def total_object_count():
    """Return the total object count based on simulator."""
    SIM_NAME = cocotb.SIM_NAME.lower()

    # Questa with VHPI
    # TODO: Why do we get massively different numbers for Questa/VHPI than for Questa/FLI or VPI?
    if SIM_NAME.startswith("modelsim") and os.environ["VHDL_GPI_INTERFACE"] == "vhpi":
        if os.environ.get("COCOTB__QUESTA_MODE", "compat") == "compat":
            return 5119
        else:
            # The QIS/Qrun flow additionally finds
            # Found dec_viterbi_ent.#IMPLICIT# (<class 'cocotb.handle.IntegerObject'>) and
            # many instances that look like s__218_3 (<class 'cocotb.handle.LogicObject'>)
            # Tracked as Siemens issue QSIM-84124.
            return 5384

    if SIM_NAME.startswith(
        (
            "ncsim",
            "xmsim",
            "modelsim",
            "riviera",
        )
    ):
        return 2663

    return 0


@cocotb.test(skip=(total_object_count() == 0))
async def recursive_discovery(dut):
    """Recursively discover every single object in the design."""

    pass_total = total_object_count()

    tlog = logging.getLogger("cocotb.test")
    await Timer(100)

    def dump_all_the_things(parent):
        if not isinstance(
            parent,
            (
                HierarchyObject,
                HierarchyArrayObject,
                ArrayObject,
            ),
        ):
            return 0
        count = 0
        for thing in parent:
            count += 1
            tlog.info("Found %s (%s)", thing._path, type(thing))
            count += dump_all_the_things(thing)
        return count

    total = dump_all_the_things(dut)
    tlog.info("Found a total of %d things", total)
    assert total == pass_total


# GHDL unable to access signals in generate loops (gh-2594)
@cocotb.test(
    expect_error=IndexError if cocotb.SIM_NAME.lower().startswith("ghdl") else ()
)
async def discovery_all(dut):
    """Discover everything on top-level."""
    dut._log.info("Iterating over top-level to discover objects")
    for thing in dut:
        thing._log.info("Found something: %s", thing._path)

    dut._log.info("length of dut.inst_acs is %d", len(dut.gen_acs))
    item = dut.gen_acs[3]
    item._log.info("this is item")


@cocotb.test()
async def dual_iteration(dut):
    """Test iteration over top-level in two forked coroutines."""

    async def iteration_loop():
        for thing in dut:
            thing._log.info("Found something: %s", thing._path)
            await Timer(1)

    loop_one = cocotb.start_soon(iteration_loop())
    loop_two = cocotb.start_soon(iteration_loop())

    await Combine(loop_one, loop_two)
