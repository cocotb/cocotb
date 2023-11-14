# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import cocotb


async def whoops_async_generator():
    # the user should have used `await` here, but they wrote `yield` by accident.
    yield cocotb.triggers.Timer(1)


@cocotb.test()
async def test_forking_accidental_async_generator(dut):
    try:
        cocotb.start_soon(whoops_async_generator())
    except TypeError as e:
        assert "async generator" in str(e)
    else:
        assert False, "should have thrown"
