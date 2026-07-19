# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Helper classes to support cocotb coroutines with pytest fixtures."""

from __future__ import annotations

from inspect import isasyncgenfunction, iscoroutinefunction
from types import TracebackType
from typing import Any, Union, cast, get_args, get_origin, get_type_hints

from pytest import FixtureDef, Function

from cocotb._test_manager import TestManager
from cocotb.handle import SimHandleBase


class AsyncFixtureCachedResult(
    tuple[
        TestManager, Any, Union[tuple[BaseException, Union[TracebackType, None]], None]
    ]
):
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
    """Resolve fixture argument."""
    return arg._main_task.result() if isinstance(arg, TestManager) else arg


def is_sim_handle_base(obj: object) -> bool:
    """Check if the provided object is a subclass of the :class:`cocotb.handle.SimHandleBase` class."""
    if get_origin(obj):
        # Check return annotation:
        # -> SimHandleBase | ...:
        # -> Union[SimHandleBase, ...]:
        # -> Optional[SimHandleBase]:
        return any(map(is_sim_handle_base, get_args(obj)))

    return isinstance(obj, type) and issubclass(obj, SimHandleBase)


def is_sim_handle_fixture(fixturedef: FixtureDef) -> bool:
    """Check if the return type annotation of the fixture is a subclass of the :class:`cocotb.handle.SimHandleBase` class.

    This function inspects the fixture's return type hints, handling single type hints as well as Union or UnionType annotations.
    """
    func = fixturedef.func
    return_annotation = get_type_hints(func).get("return")

    return (
        return_annotation is not None
        and not iscoroutinefunction(func)
        and not isasyncgenfunction(func)
        and is_sim_handle_base(return_annotation)
    )


def get_sim_handle_fixture_name(item: Function) -> str | None:
    """Get name of fixture to the :class:`cocotb.handle.SimHandleBase` instance."""
    for argname in item._fixtureinfo.argnames:
        fixturedefs = item._fixtureinfo.name2fixturedefs.get(argname)

        # Fixtures can be stacked, last stacked fixture is passed to the test function as an argument
        if fixturedefs and is_sim_handle_fixture(fixturedefs[-1]):
            return argname

    return None
