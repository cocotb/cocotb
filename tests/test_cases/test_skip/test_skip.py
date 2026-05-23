# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import pytest

import cocotb
from cocotb.triggers import Timer


@cocotb.test
async def test_skip(_: object) -> None:
    pytest.skip("This test is skipped")
    assert False  # This should not be reached


@cocotb.test
async def test_skip_in_task(_: object) -> None:
    async def skipit() -> None:
        pytest.skip("This test is skipped")
        assert False  # This should not be reached

    task = cocotb.start_soon(skipit())
    await Timer(1)
    await task
    assert False  # This should not be reached


@cocotb.test
@cocotb.skipif(True, reason="This test is skipped")
async def test_skipif_deco(_: object) -> None:
    assert False  # This test should not be run


@cocotb.skipif(True)
@cocotb.test
async def test_skip_arg(_: object) -> None:
    assert False  # This test should not be run
