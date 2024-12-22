# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import sys
from typing import Any

import cocotb


def make_failure_file() -> None:
    open("test_failed", "w").close()


@cocotb.test(_expect_sim_failure=True)
async def test_sys_exit(_: Any) -> None:
    sys.exit(1)
    make_failure_file()


@cocotb.test(_expect_sim_failure=True)
async def test_sys_exit_sim_continued(_: Any) -> None:
    make_failure_file()


@cocotb.test(_expect_sim_failure=True)
async def test_task_sys_exit(_: Any) -> None:
    async def coro():
        sys.exit(1)

    await cocotb.start_soon(coro())
    make_failure_file()


@cocotb.test(_expect_sim_failure=True)
async def test_task_sys_exit_sim_continued(_: Any) -> None:
    make_failure_file()


@cocotb.test(_expect_sim_failure=True)
async def test_keyboard_interrupt(_: Any) -> None:
    raise KeyboardInterrupt  # Analogous to Ctrl-C
    make_failure_file()


@cocotb.test(_expect_sim_failure=True)
async def test_keyboard_interrupt_sim_continued(_: Any) -> None:
    make_failure_file()


@cocotb.test(_expect_sim_failure=True)
async def test_task_keyboard_interrupt(_: Any) -> None:
    async def coro():
        raise KeyboardInterrupt  # Analogous to Ctrl-C

    await cocotb.start_soon(coro())
    make_failure_file()


@cocotb.test(_expect_sim_failure=True)
async def test_task_keyboard_interrupt_sim_continued(_: Any) -> None:
    make_failure_file()
