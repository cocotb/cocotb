# Copyright cocotb contributors
# Copyright (c) 2015 Potential Ventures Ltd
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import logging

import cocotb
from cocotb.handle import (
    ArrayObject,
    GPIDiscovery,
    HierarchyArrayObject,
    HierarchyObject,
    PackedObject,
)

SIM_NAME = cocotb.SIM_NAME.lower()

# VCS does not provide access to VHDL instances below a Verilog toplevel through
# VHPI. Its VPI returns the VHDL instances, but not the objects inside them.
vcs_vhdl_below_verilog = cocotb.xfail(
    "vcs" in SIM_NAME,
    reason="VCS does not provide access to VHDL below a Verilog toplevel",
    raises=AssertionError,
)

########################################################################################
# This is testing handle caching, so it must come first!
########################################################################################


@vcs_vhdl_below_verilog
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
            HierarchyObject,
            HierarchyArrayObject,
            ArrayObject,
        ),
    ):
        return 0
    count = 0
    for thing in parent:
        count += 1
        log.info("Found %s (%s)", thing._path, type(thing))
        count += recursive_dump(thing, log)
    return count


@vcs_vhdl_below_verilog
@cocotb.test
async def recursive_discovery(dut):
    """Recursively discover every single object in the design."""
    expected = 275

    tlog = logging.getLogger("cocotb.test")
    actual = recursive_dump(dut, tlog)

    assert expected == actual
    tlog.info("Found a total of %d things", actual)

    assert isinstance(dut.i_verilog.uart1.baud_gen_1.baud_freq, PackedObject)


@vcs_vhdl_below_verilog
@cocotb.test
async def recursive_discovery_boundary(dut):
    """Iteration through the boundary works but this just double checks."""
    expected = 160

    tlog = logging.getLogger("cocotb.test")
    actual = recursive_dump(dut.i_vhdl, tlog)
    tlog.info("Found a total of %d things", actual)
    assert actual == expected
