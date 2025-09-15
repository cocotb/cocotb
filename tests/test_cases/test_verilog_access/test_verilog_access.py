# Copyright cocotb contributors
# Copyright (c) 2015 Potential Ventures Ltd
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import cocotb
from cocotb.handle import HierarchyObject, LogicArrayObject, LogicObject


@cocotb.test()
async def port_not_hierarchy(dut):
    """
    Test for issue raised by Luke - iteration causes a toplevel port type to
    change from LogicObject to HierarchyObject
    """

    assert isinstance(dut.clk, LogicObject)
    assert isinstance(dut.i_verilog, HierarchyObject)
    assert isinstance(dut.i_verilog.clock, LogicObject)
    assert isinstance(dut.i_verilog.tx_data, LogicArrayObject)

    for _ in dut:
        pass

    for _ in dut.i_verilog:
        pass

    assert isinstance(dut.clk, LogicObject)
    assert isinstance(dut.i_verilog, HierarchyObject)
    assert isinstance(dut.i_verilog.clock, LogicObject)
    assert isinstance(dut.i_verilog.tx_data, LogicArrayObject)
