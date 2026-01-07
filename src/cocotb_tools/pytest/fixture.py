# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Helper classes to support cocotb coroutines with pytest fixtures."""

from __future__ import annotations

from typing import Any

from cocotb.task import Task


class AsyncFixture(Task):
    """Asynchronous fixture."""


class AsyncFixtureCachedResult(tuple):
    """Cached result from asynchronous fixture.

    Class compatible with pytest fixture cached result.
    Pytest is expecting 3-elements tuple: (result, cache_key, None) or
    (None, cache_key, (exception, exception.__traceback__)).

    Unfortunately, it must be valid before asynchronous task.
    In this case, asynchronous cache result will contain (task, cache_key, None)
    and result will be obtained later.

    Summary:

        (task, cache_key, None)                 - asynchronous task not completed (default)
        (result, cache_key, None)               - asynchronous task completed successfully
        (None, cache_key, (e, e.__traceback__)) - asynchronous task completed with exception
    """

    def __getitem__(self, index: Any) -> Any:
        """Dynamically get result from asynchronous task."""
        task: Task = super().__getitem__(0)

        if not task.done() or index == 1:
            return super().__getitem__(index)

        exception: BaseException | None = task.exception()

        if index == 0:
            return None if exception else task.result()

        if index == 2 and exception:
            return (exception, exception.__traceback__)

        return None


def resolve_fixture_arg(arg: Any) -> Any:
    """Resolve fixture argument."""
    return arg.result() if isinstance(arg, AsyncFixture) else arg
