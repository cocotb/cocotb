from __future__ import annotations

import logging

import cocotb
from cocotb.handle import LogicArrayObject, LogicObject
from cocotb_tools import _env


@cocotb.test(skip=_env.get("TOPLEVEL_LANG") != "vhdl")
async def test_debug_array_vhdl(dut):
    log = logging.getLogger("cocotb.test")

    log.info("Inspecting VHDL signals")

    # test_a: std_logic_vector
    assert isinstance(dut.test_a, LogicArrayObject)
    bit_a0 = dut.test_a[0]
    log.info("test_a[0] -> %s", type(bit_a0))
    assert isinstance(bit_a0, LogicObject)

    # test_b: array of std_logic
    assert isinstance(dut.test_b, LogicArrayObject)
    bit_b0 = dut.test_b[0]
    log.info("test_b[0] -> %s", type(bit_b0))
    assert isinstance(bit_b0, LogicObject)


@cocotb.test(skip=_env.get("TOPLEVEL_LANG") != "verilog")
async def test_debug_array_verilog(dut):
    log = logging.getLogger("cocotb.test")

    log.info("Inspecting Verilog signals")

    # Packed vectors
    assert isinstance(dut.test_a, LogicArrayObject)
    assert isinstance(dut.test_b, LogicArrayObject)

    # Verilog packed vectors MUST NOT be indexable
    try:
        _ = dut.test_a[0]
    except TypeError:
        log.info("Correct: Verilog packed vector is not indexable")
    else:
        raise AssertionError("Verilog packed vector should not be indexable")
