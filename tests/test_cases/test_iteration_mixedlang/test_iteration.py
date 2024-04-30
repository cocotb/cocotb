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


def recursive_dump(parent, log):
    """
    Recursively iterate through every object and log a message

    Returns a count of the total number of objects found
    """
    if not isinstance(
        parent,
        (
            cocotb.handle.HierarchyObjectBase,
            cocotb.handle.IndexableValueObjectBase,
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
    if cocotb.SIM_NAME.lower().startswith("ncsim"):
        # vpiAlways = 31 and vpiStructVar = 2 do not show up in IUS/Xcelium
        pass_total = 975
    elif cocotb.SIM_NAME.lower().startswith("xmsim"):
        # Xcelium sometimes doesn't find bits in a std_logic_vector
        pass_total = 1201
    elif cocotb.SIM_NAME.lower().startswith("modelsim"):
        pass_total = 1276
    else:
        pass_total = 1024

    tlog = logging.getLogger("cocotb.test")
    total = recursive_dump(dut, tlog)

    assert pass_total == total, "Expected %d but found %d" % (pass_total, total)
    tlog.info("Found a total of %d things", total)

    assert isinstance(
        dut.i_verilog.uart1.baud_gen_1.baud_freq, cocotb.handle.LogicObject
    ), (
        "Expected dut.i_verilog.uart1.baud_gen_1.baud_freq to be modifiable"
        f" but it was {type(dut.i_verilog.uart1.baud_gen_1.baud_freq).__name__}"
    )


@cocotb.test
async def recursive_discovery_boundary(dut):
    """Iteration through the boundary works but this just double checks."""
    if cocotb.SIM_NAME.lower().startswith("ncsim"):
        pass_total = 462
    elif cocotb.SIM_NAME.lower().startswith("xmsim"):
        # Xcelium sometimes doesn't find bits in a std_logic_vector
        pass_total = 744
    else:
        pass_total = 819

    tlog = logging.getLogger("cocotb.test")
    total = recursive_dump(dut.i_vhdl, tlog)
    tlog.info("Found a total of %d things", total)
    assert total == pass_total, "Expected %d objects but found %d" % (pass_total, total)
