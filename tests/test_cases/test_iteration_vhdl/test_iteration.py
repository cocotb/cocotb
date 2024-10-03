# Copyright (c) 2015, 2018 Potential Ventures Ltd
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import logging
import os

import cocotb
from cocotb.triggers import Combine, Timer


def total_object_count():
    """Return the total object count based on simulator."""
    SIM_NAME = cocotb.SIM_NAME.lower()

    # Questa with VHPI
    # TODO: Why do we get massively different numbers for Questa/VHPI than for Questa/FLI or VPI?
    if SIM_NAME.startswith("modelsim") and os.environ["VHDL_GPI_INTERFACE"] == "vhpi":
        return 5119

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
                cocotb.handle.HierarchyObjectBase,
                cocotb.handle.ArrayObject,
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
