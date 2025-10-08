# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""A collection of triggers which a testbench can :keyword:`await`."""

from __future__ import annotations

import logging
import sys
import warnings
from abc import abstractmethod
from collections.abc import Generator
from contextlib import AbstractAsyncContextManager
from functools import cached_property
from typing import Callable

from cocotb import debug
from cocotb._deprecation import deprecated
from cocotb._utils import pointer_str

if sys.version_info >= (3, 10):
    from typing import ParamSpec

    P = ParamSpec("P")

if sys.version_info >= (3, 11):
    from typing import Self


class TriggerCallback:
    """A cancellable handle to a callback registered with a Trigger."""

    __slots__ = ("_trigger", "_func", "_args", "_kwargs")

    def __init__(
        self,
        trigger: Trigger,
        func: Callable[P, object],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        self._trigger = trigger
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def cancel(self) -> None:
        self._trigger._deregister(self)


class Trigger:
    """A future event that a Task can wait upon."""

    def __init__(self) -> None:
        self._callbacks: dict[TriggerCallback, None] = {}

    @cached_property
    def _log(self) -> logging.Logger:
        return logging.getLogger(f"cocotb.{type(self).__qualname__}.0x{id(self):x}")

    def _register(
        self, func: Callable[P, object], *args: P.args, **kwargs: P.kwargs
    ) -> TriggerCallback:
        """Add a callback to be called when the Trigger fires."""
        if debug.debug:
            self._log.debug(
                "Registering on %s: %s, args=%s, kwargs=%s",
                self,
                func,
                args,
                kwargs,
            )
        handle = TriggerCallback(self, func, *args, **kwargs)
        do_prime = not self._callbacks
        self._callbacks[handle] = None
        # *Must* call `_prime()` after adding callback in case `_prime()` immediately
        # calls `_react()`
        # TODO Don't allow `_prime()` to call `_react()`?
        if do_prime:
            self._prime()
        return handle

    def _deregister(self, callback: TriggerCallback) -> None:
        """Remove a callback from a Trigger before it fires."""
        if debug.debug:
            self._log.debug(
                "De-registering on %s: %s, args=%s, kwargs=%s",
                self,
                callback._func,
                callback._args,
                callback._kwargs,
            )
        del self._callbacks[callback]
        if not self._callbacks:
            self._unprime()

    def _do_callbacks(self) -> None:
        callbacks, self._callbacks = self._callbacks, {}
        for cb in callbacks:
            if debug.debug:
                self._log.debug(
                    "Running after %s: %s, args=%s, kwargs=%s",
                    self,
                    cb._func,
                    cb._args,
                    cb._kwargs,
                )
            cb._func(*cb._args, **cb._kwargs)

    def _react(self) -> None:
        """Function called when a Trigger fires.

        Expected to call ``_do_callbacks()`` and any cleanup of the underlying mechanism
        required after it fires.
        """
        if debug.debug:
            self._log.debug("Fired %s", self)
        self._do_callbacks()

    @abstractmethod
    def _prime(self) -> None:
        """Enable the underlying mechanism for the Trigger to fire.

        The underlying mechanism should call this Trigger's ``_react()`` when it fires.
        """

    @abstractmethod
    def _unprime(self) -> None:
        """Disable the underlying mechanism for the Trigger to fire."""

    def __await__(self) -> Generator[Self, None, Self]:
        yield self
        return self


class _Event(Trigger):
    """Unique instance used by the Event object.

    One created for each attempt to wait on the event so that the scheduler
    can maintain a unique mapping of triggers to tasks.
    """

    _callback: Callable[[_Event], None]

    def __init__(self, parent: Event) -> None:
        super().__init__()
        self._parent = parent

    def _prime(self) -> None:
        if self._parent.is_set():
            # If the event is already set, we need to call the callback
            # immediately, so we don't need to wait for the scheduler.
            return self._react()

    def _unprime(self) -> None:
        pass

    def __repr__(self) -> str:
        return f"<{self._parent!r}.wait() at {pointer_str(self)}>"


class Event:
    r"""A way to signal an event across :class:`~cocotb.task.Task`\ s.

    :keyword:`await`\ ing the result of :meth:`wait()` will block the :keyword:`await`\ ing :class:`~cocotb.task.Task`
    until :meth:`set` is called.

    Args:
        name: Name for the Event.

    Usage:
        .. code-block:: python

            e = Event()


            async def task1():
                await e.wait()
                print("resuming!")


            cocotb.start_soon(task1())
            # do stuff
            e.set()
            await NullTrigger()  # allows task1 to execute
            # resuming!

    .. versionremoved:: 2.0

        Removed the undocumented *data* attribute and argument to :meth:`set`,
        and the *name* attribute and argument to the constructor.
    """

    def __init__(self, name: str | None = None) -> None:
        self._event: _Event = _Event(self)
        self._name: str | None = None
        if name is not None:
            warnings.warn(
                "The 'name' argument will be removed in a future release.",
                DeprecationWarning,
                stacklevel=2,
            )
            self.name = name
        self._fired: bool = False
        self._data: object = None

    @property
    @deprecated("The 'name' field will be removed in a future release.")
    def name(self) -> str | None:
        """Name of the Event.

        .. deprecated:: 2.0
            The *name* field will be removed in a future release.
        """
        return self._name

    @name.setter
    @deprecated("The 'name' field will be removed in a future release.")
    def name(self, new_name: str | None) -> None:
        self._name = new_name

    @property
    @deprecated("The data field will be removed in a future release.")
    def data(self) -> object:
        """The data associated with the Event.

        .. deprecated:: 2.0
            The data field will be removed in a future release.
            Use a separate variable to store the data instead.
        """
        return self._data

    @data.setter
    @deprecated("The data field will be removed in a future release.")
    def data(self, new_data: object) -> None:
        self._data = new_data

    def set(self, data: object | None = None) -> None:
        """Set the Event and unblock all Tasks blocked on this Event."""
        self._fired = True
        if data is not None:
            warnings.warn(
                "The data field will be removed in a future release.",
                DeprecationWarning,
                stacklevel=2,
            )
        self._data = data
        self._event._react()

    def wait(self) -> Trigger:
        """Block the current Task until the Event is set.

        If the event has already been set, the trigger will fire immediately.

        To set the Event call :meth:`set`.
        To reset the Event (and enable the use of :meth:`wait` again),
        call :meth:`clear`.
        """
        return self._event

    def clear(self) -> None:
        """Clear this event that has been set.

        Subsequent calls to :meth:`~cocotb.triggers.Event.wait` will block until
        :meth:`~cocotb.triggers.Event.set` is called again.
        """
        self._fired = False

    def is_set(self) -> bool:
        """Return ``True`` if event has been set."""
        return self._fired

    def __repr__(self) -> str:
        if self._name is None:
            fmt = "<{0} at {2}>"
        else:
            fmt = "<{0} for {1} at {2}>"
        return fmt.format(type(self).__qualname__, self._name, pointer_str(self))


class _InternalEvent(Trigger):
    """Event used internally for triggers that need cross-:class:`~cocotb.task.Task` synchronization.

    This Event can only be waited on once, by a single :class:`~cocotb.task.Task`.

    Provides transparent :func`repr` pass-through to the :class:`Trigger` using this event,
    providing a better debugging experience.
    """

    def __init__(self, parent: object) -> None:
        super().__init__()
        self._parent = parent
        self._fired: bool = False
        self._awaited: bool = False

    def _prime(self) -> None:
        if self.is_set():
            # If the event is already set, we need to call the callback
            # immediately, so we don't need to wait for the scheduler.
            return self._react()

    def _unprime(self) -> None:
        pass

    def set(self) -> None:
        """Wake up coroutine blocked on this event."""
        self._fired = True
        self._react()

    def is_set(self) -> bool:
        """Return true if event has been set."""
        return self._fired

    def __await__(
        self,
    ) -> Generator[Self, None, Self]:
        if self._awaited:
            raise RuntimeError("Only one Task may await this Trigger")
        self._awaited = True
        return (yield from super().__await__())

    def __repr__(self) -> str:
        return repr(self._parent)


class _Lock(Trigger):
    """Unique instance used by the Lock object.

    One created for each attempt to acquire the Lock so that the scheduler
    can maintain a unique mapping of triggers to tasks.
    """

    def __init__(self, parent: Lock) -> None:
        super().__init__()
        self._parent = parent

    def _prime(self) -> None:
        self._parent._prime_lock(self)

    def _unprime(self) -> None:
        self._parent._unprime_lock(self)

    def __await__(self) -> Generator[Self, None, Self]:
        if self._parent._is_used(self):
            raise RuntimeError(
                "Lock.acquire() result can only be used by one task at a time"
            )
        return (yield from super().__await__())

    def __repr__(self) -> str:
        return f"<{self._parent!r}.acquire() at {pointer_str(self)}>"


class Lock(AbstractAsyncContextManager[None]):
    """A mutual exclusion lock.

    Guarantees fair scheduling.
    Lock acquisition is given in order of attempted lock acquisition.

    Usage:
        By directly calling :meth:`acquire` and :meth:`release`.

        .. code-block:: python

            lock = Lock()
            ...
            await lock.acquire()
            try:
                # do some stuff
                ...
            finally:
                lock.release()

        Or...

        .. code-block:: python

            async with Lock():
                # do some stuff
                ...

    .. versionchanged:: 1.4

        The lock can be used as an asynchronous context manager in an
        :keyword:`async with` statement
    """

    def __init__(self, name: str | None = None) -> None:
        self._pending_primed: list[_Lock] = []
        self._name: str | None = None
        if name is not None:
            warnings.warn(
                "The 'name' argument will be removed in a future release.",
                DeprecationWarning,
                stacklevel=2,
            )
            self._name = name
        self._current_acquired: _Lock | None = None

    @property
    @deprecated("The 'name' field will be removed in a future release.")
    def name(self) -> str | None:
        """Name of the Lock.

        .. deprecated:: 2.0
            The *name* field will be removed in a future release.
        """
        return self._name

    @name.setter
    @deprecated("The 'name' field will be removed in a future release.")
    def name(self, new_name: str | None) -> None:
        self._name = new_name

    def locked(self) -> bool:
        """Return ``True`` if the lock has been acquired.

        .. versionchanged:: 2.0
            This is now a method to match :meth:`asyncio.Lock.locked`, rather than an attribute.
        """
        return self._current_acquired is not None

    def _acquire_and_fire(self, lock: _Lock) -> None:
        self._current_acquired = lock
        lock._react()

    def _prime_lock(self, lock: _Lock) -> None:
        if self._current_acquired is None:
            self._acquire_and_fire(lock)
        else:
            self._pending_primed.append(lock)

    def _unprime_lock(self, lock: _Lock) -> None:
        if lock in self._pending_primed:
            self._pending_primed.remove(lock)

    def _is_used(self, lock: _Lock) -> bool:
        return lock is self._current_acquired or lock in self._pending_primed

    def acquire(self) -> Trigger:
        """Produce a trigger which fires when the lock is acquired."""
        return _Lock(self)

    def release(self) -> None:
        """Release the lock."""
        if self._current_acquired is None:
            raise RuntimeError(f"Attempt to release an unacquired Lock {self!s}")

        self._current_acquired = None

        # nobody waiting for this lock
        if not self._pending_primed:
            return

        lock = self._pending_primed.pop(0)
        self._acquire_and_fire(lock)

    def __repr__(self) -> str:
        if self._name is None:
            fmt = "<{0} [{2} waiting] at {3}>"
        else:
            fmt = "<{0} for {1} [{2} waiting] at {3}>"
        return fmt.format(
            type(self).__qualname__,
            self._name,
            len(self._pending_primed),
            pointer_str(self),
        )

    async def __aenter__(self) -> None:
        await self.acquire()

    async def __aexit__(self, *args: object) -> None:
        self.release()


class NullTrigger(Trigger):
    """Trigger that fires immediately.

    Mostly useful when building or using higher-order functions which need to take or return Triggers.

    The scheduling order of the Task awaiting this Trigger with respect to any other Task is not deterministic
    and should generally not be relied upon.
    Instead of using this Trigger to push the Task until "after" another Task has run,
    use other synchronization techniques, such as using an :class:`.Event`.

    **Do not** do this:

    .. code-block:: python
        :class: removed

        transaction_data = None


        def monitor(dut):
            while dut.valid.value != 1 and dut.ready.value != 1:
                await RisingEdge(dut.clk)
            transaction_data = dut.data.value


        def use_transaction(dut):
            while True:
                await RisingEdge(dut.clk)
                # We need the NullTrigger here because both Tasks react to RisingEdge,
                # but there's no guarantee about which Task is run first,
                # so we need to force this one to run "later" using NullTrigger.
                await NullTrigger()
                if transaction_data is not None:
                    process(transaction_data)


        use_task = cocotb.start_soon(use_transaction(cocotb.top))
        monitor_task = cocotb.start_soon(monitor(cocotb.top))

    Instead use an :class:`!Event` to explicitly synchronize the two Tasks, like so:

    .. code-block:: python
        :class: new

        transaction_data = None
        transaction_event = Event()


        def monitor(dut):
            while dut.valid.value != 1 and dut.ready.value != 1:
                await RisingEdge(dut.clk)
            transaction_data = dut.data.value
            transaction_event.set()


        def use_transaction(dut):
            # Now we don't need the NullTrigger.
            # This Task will wake up *strictly* after `monitor_task` sets the transaction.
            await transaction_event.wait()
            process(transaction_data)


        use_task = cocotb.start_soon(use_transaction(cocotb.top))
        monitor_task = cocotb.start_soon(monitor(cocotb.top))

    .. versionremoved:: 2.0
        The *outcome* parameter was removed. There is no alternative.
    """

    def __init__(self, name: str | None = None) -> None:
        super().__init__()
        self.name = name

    def _prime(self) -> None:
        self._react()

    def _unprime(self) -> None:
        pass

    def __repr__(self) -> str:
        if self.name is None:
            fmt = "<{0} at {2}>"
        else:
            fmt = "<{0} for {1} at {2}>"
        return fmt.format(type(self).__qualname__, self.name, pointer_str(self))
