# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import sys
from typing import Any

import cocotb
from cocotb.regression import SimFailure
from cocotb.triggers import Timer


def make_failure_file() -> None:
    open("test_failed", "w").close()


@cocotb.test(expect_error=SystemExit)
async def test_sys_exit(_: Any) -> None:
    sys.exit(1)
    make_failure_file()


@cocotb.test(expect_error=SimFailure)
async def test_sys_exit_sim_continued(_: Any) -> None:
    make_failure_file()


@cocotb.test(expect_error=SystemExit)
async def test_task_sys_exit(_: Any) -> None:
    async def coro() -> None:
        sys.exit(1)

    cocotb.start_soon(coro())
    await Timer(1)
    make_failure_file()


@cocotb.test(expect_error=SimFailure)
async def test_task_sys_exit_sim_continued(_: Any) -> None:
    make_failure_file()


@cocotb.test(expect_error=SystemExit)
async def test_trigger_sys_exit(_: Any) -> None:
    await Timer(1)
    sys.exit(1)
    make_failure_file()


@cocotb.test(expect_error=SimFailure)
async def test_trigger_sys_exit_sim_continued(_: Any) -> None:
    make_failure_file()


@cocotb.test(expect_error=KeyboardInterrupt)
async def test_keyboard_interrupt(_: Any) -> None:
    raise KeyboardInterrupt  # Analogous to Ctrl-C
    make_failure_file()


@cocotb.test(expect_error=SimFailure)
async def test_keyboard_interrupt_sim_continued(_: Any) -> None:
    make_failure_file()


@cocotb.test(expect_error=KeyboardInterrupt)
async def test_task_keyboard_interrupt(_: Any) -> None:
    async def coro() -> None:
        raise KeyboardInterrupt  # Analogous to Ctrl-C

    cocotb.start_soon(coro())
    await Timer(1)
    make_failure_file()


@cocotb.test(expect_error=SimFailure)
async def test_task_keyboard_interrupt_sim_continued(_: Any) -> None:
    make_failure_file()


@cocotb.test(expect_error=KeyboardInterrupt)
async def test_trigger_keyboard_interrupt(_: Any) -> None:
    await Timer(1)
    raise KeyboardInterrupt  # Analogous to Ctrl-C
    make_failure_file()


@cocotb.test(expect_error=SimFailure)
async def test_trigger_keyboard_interrupt_sim_continued(_: Any) -> None:
    make_failure_file()
