from __future__ import annotations

import logging

import cocotb


@cocotb.test()
async def test_debug_array_verilog(dut):
    tlog = logging.getLogger("cocotb.test")

    def inspect_signal(signal, signal_name="name"):
        tlog.critical(f"Signal name: {signal_name} {type(signal)}")

    # TODO
    # un-comment after PR #5272 is merged
    # inspect_signal(dut.test_a)
    # assert type(dut.test_a) is PackedObject
    # inspect_signal(dut.test_b)
    # assert type(dut.test_a) is PackedObject

    try:
        dut.test_a[0]
    except TypeError:
        tlog.info("Packed Object indexing failed as expected")
    except AttributeError:
        tlog.info("Packed Object indexing failed as expected")
        pass
    else:
        raise AssertionError("Verilog packed vector should not be indexable")
