from __future__ import annotations

import logging

import cocotb
from cocotb.handle import (
    LogicArrayObject,
    LogicObject,
)


@cocotb.test()
async def test_debug_array(dut):
    tlog = logging.getLogger("cocotb.test")

    # Suggested Work around for VHDL vectors indexing
    # but this no longer works
    # def get_elem(logic_array: LogicArrayObject, idx: int) -> LogicObject:
    #     return cocotb.handle._make_sim_object(logic_array._handle.get_handle_by_index(idx))

    def inspect_signal(signal, signal_name="name"):
        tlog.critical(f"Signal name: {signal_name} {type(signal)}")

    inspect_signal(dut.test_a)
    assert type(dut.test_a) is LogicArrayObject
    inspect_signal(dut.test_b)
    assert type(dut.test_a) is LogicArrayObject
    inspect_signal(dut.test_a[0], "test_a[0]")
    assert type(dut.test_a) is LogicObject

    return True
