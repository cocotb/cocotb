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
import pytest
from cocotb.handle import EnumObject, HierarchyObject, IntegerObject, LogicObject


# GHDL discovers enum as `vpiNet` (gh-2600)
@cocotb.test(expect_fail=cocotb.SIM_NAME.lower().startswith("ghdl"))
async def check_enum_object(dut):
    """
    Enumerations currently behave as normal signals

    TODO: Implement an EnumObject class and detect valid string mappings
    """
    assert isinstance(dut.inst_ram_ctrl.write_ram_fsm, EnumObject)


# GHDL unable to access signals in generate loops (gh-2594)
@cocotb.test(
    expect_error=IndexError if cocotb.SIM_NAME.lower().startswith("ghdl") else ()
)
async def check_objects(dut):
    """
    Check the types of objects that are returned
    """
    tlog = logging.getLogger("cocotb.test")

    def check_instance(obj, objtype):
        assert isinstance(
            obj, objtype
        ), f"Expected {obj._path} to be of type {objtype.__name__} but got {type(obj).__name__}"
        tlog.info(f"{obj._path} is {type(obj).__name__}")

    # Hierarchy checks
    check_instance(dut.inst_axi4s_buffer, HierarchyObject)
    check_instance(dut.gen_branch_distance[0], HierarchyObject)
    check_instance(dut.gen_branch_distance[0].inst_branch_distance, HierarchyObject)
    check_instance(dut.gen_acs[0].inbranch_tdata_low, LogicObject)
    check_instance(dut.gen_acs[0].inbranch_tdata_low[0], LogicObject)
    check_instance(dut.aclk, LogicObject)
    check_instance(dut.s_axis_input_tdata, LogicObject)
    check_instance(dut.current_active, IntegerObject)
    check_instance(dut.inst_axi4s_buffer.DATA_WIDTH, IntegerObject)
    check_instance(dut.inst_ram_ctrl, HierarchyObject)

    assert (
        dut.inst_axi4s_buffer.DATA_WIDTH.value == 32
    ), f"Expected dut.inst_axi4s_buffer.DATA_WIDTH to be 32 but got {dut.inst_axi4s_buffer.DATA_WIDTH.value}"

    with pytest.raises(TypeError):
        dut.inst_axi4s_buffer.DATA_WIDTH.value = 42


@cocotb.test()
async def port_not_hierarchy(dut):
    """
    Test for issue raised by Luke - iteration causes a toplevel port type to
    change from LogicObject to HierarchyObject
    """
    assert isinstance(
        dut.aclk, LogicObject
    ), f"dut.aclk should be LogicObject but got {type(dut.aclk).__name__}"

    for _ in dut:
        pass

    assert isinstance(
        dut.aclk, LogicObject
    ), f"dut.aclk should be LogicObject but got {type(dut.aclk).__name__}"
