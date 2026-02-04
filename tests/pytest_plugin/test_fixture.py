# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test pytest fixtures with cocotb."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator

from pytest import fixture


@fixture(name="x")
def x_fixture() -> int:
    """Simple fixture that is returning a value."""
    return 5


@fixture(name="x_generator")
def x_generator_fixture() -> Generator[int, None, None]:
    """Simple generator fixture that is returning a value."""
    yield 10


@fixture(name="x_async")
async def x_async_fixture() -> int:
    """Simple asynchronous fixture that is returning a value."""
    return 15


@fixture(name="x_async_generator")
async def x_async_generator_fixture() -> AsyncGenerator[int, None]:
    """Simple asynchronous generator fixture that is returning a value."""
    yield 20


async def test_fixture_value(dut, x: int) -> None:
    """Test fixture."""
    assert x == 5


async def test_fixture_generator(dut, x_generator: int) -> None:
    """Test generator fixture."""
    assert x_generator == 10


async def test_fixture_asynchronous_value(dut, x_async: int) -> None:
    """Test asynchronous fixture."""
    assert x_async == 15


async def test_fixture_asynchronous_generator(dut, x_async_generator: int) -> None:
    """Test asynchronous generator fixture."""
    assert x_async_generator == 20


async def test_fixture_mix(
    dut, x: int, x_generator: int, x_async: int, x_async_generator
) -> None:
    """Test mix of non-asynchronous and asynchronous fixtures."""
    assert x == 5
    assert x_generator == 10
    assert x_async == 15
    assert x_async_generator == 20
