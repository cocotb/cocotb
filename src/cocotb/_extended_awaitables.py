# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""A collection of triggers which a testbench can :keyword:`await`."""

from abc import abstractmethod
from decimal import Decimal
from typing import (
    Any,
    Awaitable,
    Coroutine,
    Generator,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

import cocotb.handle
from cocotb._base_triggers import NullTrigger, Trigger, _InternalEvent
from cocotb._gpi_triggers import FallingEdge, RisingEdge, Timer, ValueChange
from cocotb._typing import RoundMode, TimeUnit
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


class _AggregateWaitable(Waitable[T]):
    """Base class for :class:`Combine` and :class:`First`."""

    def __init__(self, *trigger: Union[Trigger, Waitable[Any], Task[Any]]) -> None:
        self._triggers = trigger

        # Do some basic type-checking up front, rather than waiting until we
        # await them.
        allowed_types = (Trigger, Waitable, Task)
        for t in self._triggers:
            if not isinstance(t, allowed_types):
                raise TypeError(
                    f"All triggers must be instances of Trigger! Got: {type(t).__qualname__}"
                )

    def __repr__(self) -> str:
        # no _pointer_str here, since this is not a trigger, so identity
        # doesn't matter.
        return "{}({})".format(
            type(self).__qualname__,
            ", ".join(repr(t) for t in self._triggers),
        )


async def _wait_callback(trigger: Awaitable[T]) -> T:
    return await trigger


class Combine(_AggregateWaitable["Combine"]):
    r"""Trigger that fires when all *triggers* have fired.

    :keyword:`await`\ ing this returns the :class:`Combine` object.
    This is similar to Verilog's ``join``.
    See :ref:`combine-tutorial` for an example.

    Args:
        trigger: One or more :keyword:`await`\ able objects.

    Raises:
        TypeError: When an unsupported *trigger* object is passed.
    """

    async def _wait(self) -> "Combine":
        if len(self._triggers) == 0:
            await NullTrigger()
        elif len(self._triggers) == 1:
            await self._triggers[0]
        else:
            waiters: List[Task[object]] = []
            completed: List[Task[object]] = []
            done = _InternalEvent(self)
            exception: Union[BaseException, None] = None

            def on_done(
                task: Task[object],
            ) -> None:
                # have to check cancelled first otherwise exception() will throw
                if task.cancelled():
                    completed.append(task)
                    if len(completed) == len(waiters):
                        done.set()
                    return
                e = task.exception()
                if e is not None:
                    nonlocal exception
                    exception = e
                    done.set()
                else:
                    completed.append(task)
                    if len(completed) == len(waiters):
                        done.set()

            # start a parallel task for each trigger
            for t in self._triggers:
                task = Task[object](_wait_callback(t))
                task._add_done_callback(on_done)
                cocotb.start_soon(task)
                waiters.append(task)

            try:
                # wait for the last waiter to complete
                await done
            finally:
                # kill remaining waiters
                for w in waiters:
                    w.cancel()

            if exception is not None:
                raise exception

        return self


class First(_AggregateWaitable[object]):
    r"""Fires when the first trigger in *triggers* fires.

    :keyword:`await`\ ing this object returns the result of the first trigger that fires.
    This is similar to Verilog's ``join_any``.
    See :ref:`first-tutorial` for an example.

    Args:
        trigger: One or more :keyword:`await`\ able objects.

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
    """

    def __init__(self, *trigger: Union[Trigger, Waitable[Any], Task[Any]]) -> None:
        if not trigger:
            raise ValueError("First() requires at least one Trigger or Task argument")
        super().__init__(*trigger)

    async def _wait(self) -> object:
        if len(self._triggers) == 1:
            return await self._triggers[0]

        waiters: List[Task[object]] = []
        done = _InternalEvent(self)
        completed: List[Task[object]] = []

        def on_done(task: Task[object]) -> None:
            completed.append(task)
            done.set()

        # start a parallel task for each trigger
        for t in self._triggers:
            task = Task[object](_wait_callback(t))
            task._add_done_callback(on_done)
            cocotb.start_soon(task)
            waiters.append(task)

        try:
            # wait for a waiter to complete
            await done
        finally:
            # kill all the other waiters
            for w in waiters:
                w.cancel()

        return completed[0].result()


class ClockCycles(Waitable["ClockCycles"]):
    r"""Finishes after *num_cycles* transitions of *signal*.

    :keyword:`await`\ ing this Trigger returns the ClockCycle object.

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
        signal: "cocotb.handle.LogicObject",
        num_cycles: int,
    ) -> None: ...

    @overload
    def __init__(
        self,
        signal: "cocotb.handle.LogicObject",
        num_cycles: int,
        edge_type: Union[
            Type[RisingEdge], Type[FallingEdge], Type[ValueChange], None
        ] = None,
    ) -> None: ...

    @overload
    def __init__(
        self, signal: "cocotb.handle.LogicObject", num_cycles: int, *, rising: bool
    ) -> None: ...

    def __init__(
        self,
        signal: "cocotb.handle.LogicObject",
        num_cycles: int,
        edge_type: Union[
            bool, Type[RisingEdge], Type[FallingEdge], Type[ValueChange], None
        ] = None,
        *,
        rising: Union[bool, None] = None,
    ) -> None:
        self._signal = signal
        self._num_cycles = num_cycles
        self._edge_type: Union[Type[RisingEdge], Type[FallingEdge], Type[ValueChange]]
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
    def signal(self) -> "cocotb.handle.LogicObject":
        """The signal being monitored."""
        return self._signal

    @property
    def num_cycles(self) -> int:
        """The number of cycles to wait."""
        return self._num_cycles

    @property
    def edge_type(
        self,
    ) -> Union[Type[RisingEdge], Type[FallingEdge], Type[ValueChange]]:
        """The type of edge trigger used."""
        return self._edge_type

    async def _wait(self) -> "ClockCycles":
        trigger = self._edge_type(self._signal)
        for _ in range(self._num_cycles):
            await trigger
        return self

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({self._signal._path}, {self._num_cycles}, {self._edge_type.__qualname__})"


class SimTimeoutError(TimeoutError):
    """Exception thrown when a timeout, in terms of simulation time, occurs."""


TriggerT = TypeVar("TriggerT", bound=Trigger)


@overload
async def with_timeout(
    trigger: TriggerT,
    timeout_time: Union[float, Decimal],
    timeout_unit: TimeUnit = "step",
    round_mode: Optional[RoundMode] = None,
) -> TriggerT: ...


@overload
async def with_timeout(
    trigger: Waitable[T],
    timeout_time: Union[float, Decimal],
    timeout_unit: TimeUnit = "step",
    round_mode: Optional[RoundMode] = None,
) -> T: ...


@overload
async def with_timeout(
    trigger: Task[T],
    timeout_time: Union[float, Decimal],
    timeout_unit: TimeUnit = "step",
    round_mode: Optional[RoundMode] = None,
) -> T: ...


@overload
async def with_timeout(
    trigger: Coroutine[Trigger, None, T],
    timeout_time: Union[float, Decimal],
    timeout_unit: TimeUnit = "step",
    round_mode: Optional[RoundMode] = None,
) -> T: ...


async def with_timeout(
    trigger: Union[TriggerT, Waitable[T], Task[T], Coroutine[Trigger, None, T]],
    timeout_time: Union[float, Decimal],
    timeout_unit: TimeUnit = "step",
    round_mode: Optional[RoundMode] = None,
) -> Union[T, TriggerT]:
    r"""Wait on triggers or coroutines, throw an exception if it waits longer than the given time.

    When a :term:`python:coroutine` is passed,
    the callee coroutine is started,
    the caller blocks until the callee completes,
    and the callee's result is returned to the caller.
    If timeout occurs, the callee is killed
    and :exc:`SimTimeoutError` is raised.

    When a :term:`task` is passed,
    the caller blocks until the callee completes
    and the callee's result is returned to the caller.
    If timeout occurs, the callee `continues to run`
    and :exc:`SimTimeoutError` is raised.

    If a :class:`~cocotb.triggers.Trigger` or :class:`~cocotb.triggers.Waitable` is passed,
    the caller blocks until the trigger fires,
    and the trigger is returned to the caller.
    If timeout occurs, the trigger is cancelled
    and :exc:`SimTimeoutError` is raised.

    Usage:
        .. code-block:: python

            await with_timeout(coro, 100, "ns")
            await with_timeout(First(coro, event.wait()), 100, "ns")

    Args:
        trigger:
            A single object that could be right of an :keyword:`await` expression in cocotb.
        timeout_time:
            Simulation time duration before timeout occurs.
        timeout_unit:
            Unit of timeout_time, accepts any unit that :class:`~cocotb.triggers.Timer` does.
        round_mode:
            String specifying how to handle time values that sit between time steps
            (one of ``'error'``, ``'round'``, ``'ceil'``, ``'floor'``, ``None``).
            A ``None`` argument is converted to the current value of :attr:`.Timer.round_mode`.

    Returns:
        First trigger that completed if timeout did not occur.

    Raises:
        :exc:`SimTimeoutError`: If timeout occurs.

    .. versionadded:: 1.3

    .. versionchanged:: 1.7
        Support passing :term:`python:coroutine`\ s.

    .. versionchanged:: 2.0
        Passing ``None`` as the *timeout_unit* argument was removed, use ``'step'`` instead.

    """
    if isinstance(trigger, Coroutine):
        trigger = cocotb.start_soon(trigger)
        shielded = False
    else:
        shielded = True
    timeout_timer = Timer(timeout_time, timeout_unit, round_mode=round_mode)
    res = await First(timeout_timer, trigger)
    if res is timeout_timer:
        if not shielded:
            # shielded = False only when trigger is a Task created to wrap a Coroutine
            task = cast("Task[object]", trigger)
            task.cancel()
        raise SimTimeoutError
    else:
        return cast("T | TriggerT", res)
