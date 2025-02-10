# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd,
#       SolarFlare Communications Inc nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""A collection of triggers which a testbench can :keyword:`await`."""

from abc import abstractmethod
from decimal import Decimal
from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Generator,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

import cocotb.handle
import cocotb.task
from cocotb._base_triggers import NullTrigger, Trigger, _InternalEvent
from cocotb._deprecation import deprecated
from cocotb._gpi_triggers import FallingEdge, RisingEdge, Timer, ValueChange
from cocotb._typing import TimeUnit

T = TypeVar("T")


class TaskComplete(Trigger, Generic[T]):
    r"""Fires when a :class:`~cocotb.task.Task` completes.

    Unlike :func:`~cocotb.triggers.Join`, this Trigger does not return the result of the Task when :keyword:`await`\ ed.

    .. note::
        It is preferable to use :attr:`.Task.complete` to get this object over calling the constructor.

    .. code-block:: python

        async def coro_inner():
            await Timer(1, unit="ns")
            raise ValueError("Oops")


        task = cocotb.start_soon(coro_inner())
        await task.complete  # no exception raised here
        assert task.exception() == ValueError("Oops")

    Args:
        task: The Task upon which to wait for completion.

    .. versionadded:: 2.0
    """

    def __new__(cls, task: "cocotb.task.Task[T]") -> "TaskComplete[T]":
        return task.complete

    @classmethod
    def _make(cls, task: "cocotb.task.Task[T]") -> "TaskComplete[T]":
        self = super().__new__(cls)
        cls.__init__(self, task)
        return self

    def __init__(self, task: "cocotb.task.Task[T]") -> None:
        super().__init__()
        self._task = task

    def _prime(self, callback: Callable[[Trigger], None]) -> None:
        if self._task.done():
            callback(self)
        else:
            super()._prime(callback)

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({self._task!s})"

    @property
    def task(self) -> "cocotb.task.Task[T]":
        """The :class:`.Task` associated with this completion event."""
        return self._task


@deprecated(
    "Using `task` directly is prefered to `Join(task)` in all situations where the latter could be used."
)
def Join(task: "cocotb.task.Task[T]") -> "cocotb.task.Task[T]":
    r"""Fires when a :class:`~cocotb.task.Task` completes and returns the Task's result.

    Equivalent to calling :meth:`task.join() <cocotb.task.Task.join>`.

    .. code-block:: python

        async def coro_inner():
            await Timer(1, unit="ns")
            return "Hello world"


        task = cocotb.start_soon(coro_inner())
        result = await Join(task)
        assert result == "Hello world"

    Args:
        task: The Task upon which to wait for completion.

    Returns:
        Object that can be :keyword:`await`\ ed or passed into :class:`~cocotb.triggers.First` or :class:`~cocotb.triggers.Combine`;
        the result of which will be the result of the Task.

    .. deprecated:: 2.0
        Using ``task`` directly is preferred to ``Join(task)`` in all situations where the latter could be used.
    """
    return task


class Waitable(Awaitable[T]):
    """Base class for trigger-like objects implemented using coroutines.

    This converts a ``_wait`` abstract method into a suitable ``__await__``.
    """

    @abstractmethod
    async def _wait(self) -> T:
        """The coroutine function which implements the functionality of the Waitable."""

    def __await__(self) -> Generator[Any, Any, T]:
        return self._wait().__await__()


class _AggregateWaitable(Waitable[T]):
    """Base class for :class:`Combine` and :class:`First`."""

    def __init__(
        self, *trigger: Union[Trigger, Waitable[Any], "cocotb.task.Task[Any]"]
    ) -> None:
        self._triggers = trigger

        # Do some basic type-checking up front, rather than waiting until we
        # await them.
        allowed_types = (Trigger, Waitable, cocotb.task.Task)
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


async def _wait_callback(
    trigger: Union[Trigger, Waitable[object], "cocotb.task.Task[object]"],
) -> object:
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
            waiters: List[cocotb.task.Task[object]] = []
            done = _InternalEvent(self)
            exception: Union[BaseException, None] = None

            def on_done(
                task: cocotb.task.Task[object],
            ) -> None:
                # have to check cancelled first otherwise exception() will throw
                if task.cancelled():
                    waiters.remove(task)
                    if not waiters:
                        done.set()
                        return
                e = task.exception()
                if e is not None:
                    nonlocal exception
                    exception = e
                    done.set()
                else:
                    waiters.remove(task)
                    if not waiters:
                        done.set()

            # start a parallel task for each trigger
            for t in self._triggers:
                task = cocotb.task.Task[object](_wait_callback(t))
                task._add_done_callback(on_done)
                cocotb.start_soon(task)
                waiters.append(task)

            # wait for the last waiter to complete
            await done

            # kill remaining waiters
            for w in waiters:
                w.kill()

            if exception is not None:
                raise exception

        return self


class First(_AggregateWaitable[Any]):
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

    def __init__(
        self, *trigger: Union[Trigger, Waitable[Any], "cocotb.task.Task[Any]"]
    ) -> None:
        if not trigger:
            raise ValueError("First() requires at least one Trigger or Task argument")
        super().__init__(*trigger)

    async def _wait(self) -> Any:
        if len(self._triggers) == 1:
            return await self._triggers[0]

        waiters: List[cocotb.task.Task[Any]] = []
        done = _InternalEvent(self)
        completed: List[cocotb.task.Task[Any]] = []

        def on_done(task: cocotb.task.Task[Any]) -> None:
            waiters.remove(task)
            completed.append(task)
            done.set()

        # start a parallel task for each trigger
        for t in self._triggers:
            task = cocotb.task.Task[Any](_wait_callback(t))
            task._add_done_callback(on_done)
            cocotb.start_soon(task)
            waiters.append(task)

        # wait for a waiter to complete
        await done

        # kill all the other waiters
        for w in waiters:
            w.kill()

        return completed[0].result()


class ClockCycles(Waitable["ClockCycles"]):
    r"""Finishes after *num_cycles* transitions of *signal*.

    :keyword:`await`\ ing this Trigger returns the ClockCycle object.

    Args:
        signal: The signal to monitor.
        num_cycles: The number of cycles to count.
        rising: If ``True``, count rising edges; if ``False``, count falling edges.
        edge: The kind of :ref:`edge-triggers` to count.

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
        _3: Union[bool, Type[RisingEdge], Type[FallingEdge], Type[ValueChange]],
    ) -> None: ...

    @overload
    def __init__(
        self, signal: "cocotb.handle.LogicObject", num_cycles: int, *, rising: bool
    ) -> None: ...

    @overload
    def __init__(
        self,
        signal: "cocotb.handle.LogicObject",
        num_cycles: int,
        *,
        edge_type: Union[Type[RisingEdge], Type[FallingEdge], Type[ValueChange]],
    ) -> None: ...

    def __init__(
        self,
        signal: "cocotb.handle.LogicObject",
        num_cycles: int,
        _3: Union[
            bool, Type[RisingEdge], Type[FallingEdge], Type[ValueChange], None
        ] = None,
        *,
        rising: Union[bool, None] = None,
        edge_type: Union[
            Type[RisingEdge], Type[FallingEdge], Type[ValueChange], None
        ] = None,
    ) -> None:
        self._signal = signal
        self._num_cycles = num_cycles
        self._edge_type: Union[Type[RisingEdge], Type[FallingEdge], Type[ValueChange]]
        if _3 is not None:
            if rising is not None or edge_type is not None:
                raise TypeError("Passed more than one edge selection argument.")
            if _3 is True:
                self._edge_type = RisingEdge
            elif _3 is False:
                self._edge_type = FallingEdge
            else:
                self._edge_type = _3
        elif rising is not None:
            if edge_type is not None:
                raise TypeError("Passed more than one edge selection argument.")
            self._edge_type = RisingEdge if rising else FallingEdge
        elif edge_type is not None:
            self._edge_type = edge_type
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


@overload
async def with_timeout(
    trigger: Trigger,
    timeout_time: Union[float, Decimal],
    timeout_unit: TimeUnit = "step",
    round_mode: Optional[str] = None,
) -> None: ...


@overload
async def with_timeout(
    trigger: Waitable[T],
    timeout_time: Union[float, Decimal],
    timeout_unit: TimeUnit = "step",
    round_mode: Optional[str] = None,
) -> T: ...


@overload
async def with_timeout(
    trigger: "cocotb.task.Task[T]",
    timeout_time: Union[float, Decimal],
    timeout_unit: TimeUnit = "step",
    round_mode: Optional[str] = None,
) -> T: ...


@overload
async def with_timeout(
    trigger: Coroutine[Any, Any, T],
    timeout_time: Union[float, Decimal],
    timeout_unit: TimeUnit = "step",
    round_mode: Optional[str] = None,
) -> T: ...


async def with_timeout(
    trigger: Union[
        Trigger, Waitable[Any], "cocotb.task.Task[Any]", Coroutine[Any, Any, Any]
    ],
    timeout_time: Union[float, Decimal],
    timeout_unit: TimeUnit = "step",
    round_mode: Optional[str] = None,
) -> Any:
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
            (one of ``'error'``, ``'round'``, ``'ceil'``, ``'floor'``).

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
            trigger = cast(cocotb.task.Task[Any], trigger)
            trigger.kill()
        raise SimTimeoutError
    else:
        return res
