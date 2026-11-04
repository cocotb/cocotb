# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""A collection of triggers which a testbench can :keyword:`await`."""

from __future__ import annotations

import warnings
from abc import abstractmethod
from collections.abc import Awaitable, Generator
from decimal import Decimal
from typing import Any, TypeVar, cast, overload

import cocotb.handle
from cocotb._base_triggers import NullTrigger, Trigger
from cocotb._concurrent_waiters import _wait, select
from cocotb._deprecation import deprecated
from cocotb._gpi_triggers import FallingEdge, RisingEdge, Timer, ValueChange
from cocotb.simtime import RoundMode, TimeUnit
from cocotb.task import Task

T = TypeVar("T")


class Waitable(Awaitable[T]):
    """A Trigger-like object that can be implemented using coroutines.

    This converts a ``_wait`` abstract method into a suitable ``__await__``.
    """

    @abstractmethod
    async def _wait(self) -> T:
        """The coroutine function which implements the functionality of the Waitable."""

    def __await__(self) -> Generator[Trigger, None, T]:
        return self._wait().__await__()


class Combine(Waitable["Combine"]):
    r"""Trigger that fires when all *triggers* have fired.

    :keyword:`await`\ ing this returns the :class:`!Combine` object.
    This is similar to Verilog's ``join``.
    See :ref:`combine-tutorial` for an example.

    Args:
        triggers: One or more :keyword:`await`\ able objects.

    Raises:
        TypeError: When an unsupported *trigger* object is passed.

    .. deprecated:: 2.1
        Passing :class:`~cocotb.task.Task` objects to :class:`!Combine` is deprecated.
        Use :func:`~cocotb.triggers.gather` instead and pass coroutines directly instead of wrapping them in :func:`cocotb.start_soon`.

    .. versionchanged:: 2.1
        Previously when a child *trigger* was cancelled, the cancellation was ignored.
        Now, if a child *trigger* is cancelled, the entire :class:`!Combine`, including all other child triggers, is cancelled,
        and a :exc:`~asyncio.CancelledError` is raised at the point the :class:`!Combine` is :keyword:`await` ed.
    """

    _task_deprecation_str = (
        "Passing Task objects to `Combine` is deprecated. "
        "Use `gather` instead and pass coroutines directly instead of wrapping them in `cocotb.start_soon`."
    )

    @overload
    def __init__(self, *triggers: Trigger | Waitable[Any]) -> None: ...

    @overload
    @deprecated(_task_deprecation_str)
    def __init__(self, *triggers: Trigger | Waitable[Any] | Task[Any]) -> None: ...

    def __init__(self, *triggers: Trigger | Waitable[Any] | Task[Any]) -> None:
        # Do some basic type-checking up front, rather than waiting until we
        # await them.
        for t in triggers:
            if isinstance(t, Task):
                warnings.warn(
                    self._task_deprecation_str, DeprecationWarning, stacklevel=2
                )
            elif not isinstance(t, (Trigger, Waitable)):
                raise TypeError(
                    f"All triggers must be instances of Trigger! Got: {type(t).__qualname__}"
                )

        self._triggers = triggers

    async def _wait(self) -> Combine:
        if len(self._triggers) == 0:
            await NullTrigger()
        else:
            idx, tasks = await _wait(
                self._triggers, return_when="FIRST_EXCEPTION", _repr=self.__repr__
            )
            if idx is not None:
                tasks[idx].result()
            return self
        return self

    def __repr__(self) -> str:
        # no _pointer_str here, since this is not a trigger, so identity
        # doesn't matter.
        return "{}({})".format(
            type(self).__qualname__,
            ", ".join(repr(t) for t in self._triggers),
        )


class First(Waitable[object]):
    r"""Fires when the first trigger in *triggers* fires.

    :keyword:`await`\ ing this object returns the result of the first trigger that fires.
    This is similar to Verilog's ``join_any``.
    See :ref:`first-tutorial` for an example.

    Args:
        triggers: One or more :keyword:`await`\ able objects.

    Raises:
        TypeError: When an unsupported *trigger* object is passed.
        ValueError: When no triggers are passed.

    .. note::
        The event loop is single threaded, so while events may be simultaneous
        in simulation time, they can never be simultaneous in real time.
        For this reason, the value of ``t_ret is t1`` in the following example
        is implementation-defined, and will vary by simulator::

            t1 = Timer(10, unit="ps")
            t2 = Timer(10, unit="ps")
            t_ret = await First(t1, t2)

    .. note::
        In the old-style :ref:`generator-based coroutines <yield-syntax>`, ``t = yield [a, b]`` was another spelling of
        ``t = yield First(a, b)``. This spelling is no longer available when using :keyword:`await`-based
        coroutines.

    .. deprecated:: 2.1
        Passing :class:`~cocotb.task.Task` objects to :class:`!First` is deprecated.
        Use :func:`~cocotb.triggers.select` instead and pass coroutines directly instead of wrapping them in :func:`cocotb.start_soon`.
    """

    _task_deprecation_str = (
        "Passing Task objects to `First` is deprecated. "
        "Use `select` instead and pass coroutines directly instead of wrapping them in `cocotb.start_soon`."
    )

    @overload
    def __init__(
        self, first: Trigger | Waitable[Any], /, *triggers: Trigger | Waitable[Any]
    ) -> None: ...

    @overload
    @deprecated(_task_deprecation_str)
    def __init__(
        self,
        first: Trigger | Waitable[Any] | Task[Any],
        /,
        *triggers: Trigger | Waitable[Any] | Task[Any],
    ) -> None: ...

    def __init__(self, *triggers: Trigger | Waitable[Any] | Task[Any]) -> None:
        if not triggers:
            raise ValueError("First() requires at least one Trigger or Task argument")

        # Do some basic type-checking up front, rather than waiting until we
        # await them.
        for t in triggers:
            if isinstance(t, Task):
                warnings.warn(
                    self._task_deprecation_str, DeprecationWarning, stacklevel=2
                )
            elif not isinstance(t, (Trigger, Waitable)):
                raise TypeError(
                    f"All triggers must be instances of Trigger! Got: {type(t).__qualname__}"
                )

        self._triggers = triggers

    async def _wait(self) -> object:
        idx, tasks = await _wait(
            self._triggers, return_when="FIRST_COMPLETED", _repr=self.__repr__
        )
        assert idx is not None
        return tasks[idx].result()

    def __repr__(self) -> str:
        # no _pointer_str here, since this is not a trigger, so identity
        # doesn't matter.
        return "{}({})".format(
            type(self).__qualname__,
            ", ".join(repr(t) for t in self._triggers),
        )


class ClockCycles(Waitable["ClockCycles"]):
    r"""Finishes after *num_cycles* transitions of *signal*.

    :keyword:`await`\ ing this Trigger returns the :class:`!ClockCycles` object.

    Args:
        signal: The signal to monitor.
        num_cycles: The number of cycles to count.
        rising: If ``True``, count rising edges; if ``False``, count falling edges.
        edge_type: The kind of :ref:`edge-triggers` to count.

    .. warning::
        On many simulators transitions occur when the signal changes value from non-``0`` to ``0`` or non-``1`` to ``1``,
        not just from ``1`` to ``0`` or ``0`` to ``1``.

    .. versionadded:: 2.0
        Passing the edge trigger type: :class:`.RisingEdge`, :class:`.FallingEdge`, or :class:`.ValueChange`
        as the third positional argument or by the keyword *edge_type*.
    """

    @overload
    def __init__(
        self,
        signal: cocotb.handle.LogicObject,
        num_cycles: int,
    ) -> None: ...

    @overload
    def __init__(
        self,
        signal: cocotb.handle.LogicObject,
        num_cycles: int,
        edge_type: type[RisingEdge | FallingEdge | ValueChange] | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self, signal: cocotb.handle.LogicObject, num_cycles: int, *, rising: bool
    ) -> None: ...

    def __init__(
        self,
        signal: cocotb.handle.LogicObject,
        num_cycles: int,
        edge_type: type[RisingEdge | FallingEdge | ValueChange] | bool | None = None,
        *,
        rising: bool | None = None,
    ) -> None:
        self._signal = signal
        self._num_cycles = num_cycles
        self._edge_type: type[RisingEdge | FallingEdge | ValueChange]
        if edge_type is not None and rising is not None:
            raise TypeError("Passed more than one edge selection argument.")
        elif edge_type is True:
            self._edge_type = RisingEdge
        elif edge_type is False:
            self._edge_type = FallingEdge
        elif edge_type is not None:
            self._edge_type = edge_type
        elif rising is not None:
            self._edge_type = RisingEdge if rising else FallingEdge
        else:
            # default if no argument is passed
            self._edge_type = RisingEdge

    @property
    def signal(self) -> cocotb.handle.LogicObject:
        """The signal being monitored."""
        return self._signal

    @property
    def num_cycles(self) -> int:
        """The number of cycles to wait."""
        return self._num_cycles

    @property
    def edge_type(
        self,
    ) -> type[RisingEdge | FallingEdge | ValueChange]:
        """The type of edge trigger used."""
        return self._edge_type

    async def _wait(self) -> ClockCycles:
        trigger = self._edge_type(self._signal)
        for _ in range(self._num_cycles):
            await trigger
        return self

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({self._signal._path}, {self._num_cycles}, {self._edge_type.__qualname__})"


class SimTimeoutError(TimeoutError):
    """Exception thrown when a timeout, in terms of simulation time, occurs."""


def with_timeout(*args: Any, **kwargs: Any) -> Any:
    r"""Wait on any awaitable, throw an exception if it waits longer than the given time.

    When a :term:`python:coroutine` is passed,
    the callee coroutine is started,
    the caller blocks until the callee completes,
    and the callee's result is returned to the caller.
    If timeout occurs, the callee is killed
    and :exc:`SimTimeoutError` is raised.

    When a :term:`task` is passed,
    the caller blocks until the callee completes
    and the callee's result is returned to the caller.
    If timeout occurs, the callee ``continues to run``
    and :exc:`SimTimeoutError` is raised.

    If a :class:`~cocotb.triggers.Trigger` or :class:`~cocotb.triggers.Waitable` is passed,
    the caller blocks until the trigger fires,
    and the trigger is returned to the caller.
    If timeout occurs, the trigger is cancelled
    and :exc:`SimTimeoutError` is raised.

    This function may also be used as a decorator. When called without an awaitable
    as the first positional argument, it returns a decorator that wraps a coroutine
    function so that awaiting it (or scheduling it) is subject to the timeout:

        .. code-block:: python

            @with_timeout(100, "ns")
            async def my_thing():
                ...

            await with_timeout(coro, 100, "ns")

    Args:
        trigger:
            A single object that could be right of an :keyword:`await` expression in cocotb.
            Omitted when used as a decorator.
        timeout_time:
            Simulation time duration before timeout occurs.
        timeout_unit:
            Unit of timeout_time, accepts any unit that :class:`~cocotb.triggers.Timer` does.
        round_mode:
            String specifying how to handle time values that sit between time steps
            (one of ``'error'``, ``'round'``, ``'ceil'``, ``'floor'``, ``None``).
            A ``None`` argument is converted to the current value of :attr:`.Timer.round_mode`.

    Returns:
        First trigger that completed if timeout did not occur, or a decorator when
        used as a decorator.

    Raises:
        :exc:`SimTimeoutError`: If timeout occurs.

    .. versionadded:: 1.3

    .. versionchanged:: 1.7
        Support passing :term:`python:coroutine`\ s.

    .. versionchanged:: 2.0
        Passing ``None`` as the *timeout_unit* argument was removed, use ``'step'`` instead.

    .. versionchanged:: 2.2
        Support using as a decorator.
    """
    import functools
    import inspect

    # Parse keyword arguments.
    timeout_time_kw = kwargs.pop("timeout_time", None)
    timeout_unit_kw = kwargs.pop("timeout_unit", None)
    round_mode_kw = kwargs.pop("round_mode", None)

    # Immediate form: first positional (or trigger kwarg) is an awaitable.
    trigger = None
    immediate = False
    if args and hasattr(args[0], "__await__"):
        trigger = args[0]
        immediate = True
    elif "trigger" in kwargs and hasattr(kwargs["trigger"], "__await__"):
        trigger = kwargs.pop("trigger")
        immediate = True

    if immediate:
        if timeout_time_kw is not None:
            tt = timeout_time_kw
        elif len(args) > 1:
            tt = args[1]
        else:
            raise TypeError("with_timeout() missing timeout_time")

        if timeout_unit_kw is not None:
            tu = timeout_unit_kw
        elif len(args) > 2:
            tu = args[2]
        else:
            tu = "step"

        if round_mode_kw is not None:
            rm = round_mode_kw
        elif len(args) > 3:
            rm = args[3]
        else:
            rm = None

        async def _run() -> Any:
            i, res = await select(Timer(tt, tu, round_mode=rm), trigger)
            if i == 0:
                raise SimTimeoutError
            return cast("T", res)

        return _run()

    # Decorator / factory form.
    # Determine timeout parameters from positional args / kwargs.
    if timeout_time_kw is not None:
        tt = timeout_time_kw
    elif args:
        tt = args[0]
    else:
        # allow trigger kwarg carrying timeout_time? no
        tt = None
    if tt is None:
        raise TypeError("with_timeout() missing timeout_time")

    if timeout_unit_kw is not None:
        tu = timeout_unit_kw
    elif len(args) > 1:
        tu = args[1]
    else:
        tu = "step"

    if round_mode_kw is not None:
        rm = round_mode_kw
    elif len(args) > 2:
        rm = args[2]
    else:
        rm = None

    def decorator(func: Any) -> Any:
        if inspect.iscoroutinefunction(func) or callable(func):

            async def wrapped(*a: Any, **kw: Any) -> Any:
                return await with_timeout(func(*a, **kw), tt, tu, rm)

            functools.update_wrapper(wrapped, func)
            return wrapped
        return func

    return decorator
