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
        thing._log.info("Found something: %s", thing._path)


@cocotb.test()
async def dual_iteration(dut):
    loop_one = cocotb.start_soon(iteration_loop(dut))
    loop_two = cocotb.start_soon(iteration_loop(dut))

    await First(loop_one, loop_two)
