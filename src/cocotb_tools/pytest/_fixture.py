# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Helper utilities and classes for supporting cocotb coroutine fixtures in pytest."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Union, cast

from cocotb._test_manager import TestManager


class AsyncFixtureCachedResult(
    tuple[
        TestManager, Any, Union[tuple[BaseException, Union[TracebackType, None]], None]
    ]
):
    """Cached result representing an asynchronous pytest fixture.

    This class implements a pytest-compatible cached result interface. Pytest expects a 3-element tuple for cached fixture results:

    * ``(result, cache_key, None)`` when successful, or
    * ``(None, cache_key, (exception, traceback))`` when failed.

    Since asynchronous tasks are executed later by the cocotb scheduler, the initial
    cached result tuple contains ``(task, cache_key, None)``. When pytest accesses
    the fixture value, this class dynamically intercepts the lookup to query the
    completed task status and returns the computed result or raises the exception.

    Summary of states:

    * ``(task, cache_key, None)``: The asynchronous task is not yet completed.
    * ``(result, cache_key, None)``: The asynchronous task completed successfully.
    * ``(None, cache_key, (e, e.__traceback__))``: The asynchronous task failed with an exception.
    """

    def __getitem__(self, index: Any) -> Any:
        """Dynamically retrieve the cached result elements.

        If the underlying async task is done, retrieves the actual value or exception.
        Otherwise, returns the pending task wrapper.

        Args:
            index: The index of the tuple element (0, 1, or 2).

        Returns:
            The requested tuple element.
        """
        task = cast("TestManager", super().__getitem__(0))._main_task

        if not task.done() or index == 1:
            return super().__getitem__(index)

        exception: BaseException | None = task.exception()

        if index == 0:
            return None if exception else task.result()

        if index == 2 and exception:
            return (exception, exception.__traceback__)

        return None


def resolve_fixture_arg(arg: Any) -> Any:
    """Resolve an asynchronous fixture argument to its completed result.

    If the argument is an instance of :class:`~cocotb._test_manager.TestManager`,
    this function retrieves and returns the result of its main task.
    Otherwise, returns the argument as-is.

    Args:
        arg: The fixture argument to resolve.

    Returns:
        The resolved value of the fixture.
    """
    return arg._main_task.result() if isinstance(arg, TestManager) else arg
