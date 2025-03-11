# Copyright (c) 2015 Potential Ventures Ltd
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
from cocotb.handle import GPIDiscovery

########################################################################################
# This is testing handle caching, so it must come first!
########################################################################################


@cocotb.test
async def discovery_method(dut) -> None:
    """Verify that the different discovery methods work."""

    # this is a Verilog toplevel, so we should not be finding a VHDL object
    # when we request NATIVE discovery, but we should get it with AUTO
    assert dut._get("i_vhdl", GPIDiscovery.NATIVE) is None
    assert dut._get("i_vhdl", GPIDiscovery.AUTO) is not None
    # Now we should see the handle has been cached and can get it with NATIVE set
    assert dut._get("i_vhdl", GPIDiscovery.NATIVE) is not None


########################################################################################


def recursive_dump(parent, log):
    """
    Recursively iterate through every object and log a message

    Returns a count of the total number of objects found
    """
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
        log.info("Found %s (%s)", thing._path, type(thing))
        count += recursive_dump(thing, log)
    return count


@cocotb.test
async def recursive_discovery(dut):
    """Recursively discover every single object in the design."""
    expected = 275

    tlog = logging.getLogger("cocotb.test")
    actual = recursive_dump(dut, tlog)

    assert expected == actual
    tlog.info("Found a total of %d things", actual)

    assert isinstance(
        dut.i_verilog.uart1.baud_gen_1.baud_freq, cocotb.handle.LogicArrayObject
    )


@cocotb.test
async def recursive_discovery_boundary(dut):
    """Iteration through the boundary works but this just double checks."""
    expected = 160

    tlog = logging.getLogger("cocotb.test")
    actual = recursive_dump(dut.i_vhdl, tlog)
    tlog.info("Found a total of %d things", actual)
    assert actual == expected
