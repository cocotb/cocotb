# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Common utilities shared by many tests in this directory
"""

from __future__ import annotations

import operator
from collections.abc import Generator
from contextlib import contextmanager
from typing import Callable

from cocotb.simtime import TimeUnit
from cocotb.utils import get_sim_steps, get_sim_time, get_time_from_sim_steps


class MyException(Exception): ...


class MyBaseException(BaseException): ...


@contextmanager
def assert_takes(
    time: float, unit: TimeUnit, cmp: Callable[[int, int], bool] = operator.eq
) -> Generator[None, None, None]:
    """Assert that the block takes a certain amount of time to finish.

    The *cmp* function passes actual after first argument and expected as the second.
    Other useful comparison functions are: :func:`math.isclose`, and the functions in the
    :mod:`operator` module.

    Args:
        time: Time value.
        unit: Unit of *time*.
        cmp: Comparison function to use. Defaults to equality.
    """
    expected = get_sim_steps(time, unit)
    start = get_sim_time("step")
    yield
    end = get_sim_time("step")
    actual = end - start
    actual_in_units = get_time_from_sim_steps(actual, unit)
    assert cmp(actual, expected), (
        f"Expected the code to take {time}{unit}, actually took {actual_in_units}{unit}"
    )
