from __future__ import annotations

import cocotb
from cocotb.triggers import Timer


@cocotb.test()
async def test_bootstrap_loading(_):
    # Bootstrap loading will fail, so this test should never run.
    await Timer(100, "ns")
