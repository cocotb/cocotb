# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""A collection of triggers which a testbench can :keyword:`await`."""

import logging
import warnings
from typing import (
    AsyncContextManager,
    Callable,
    Generator,
    List,
    Optional,
    Union,
)

from cocotb._deprecation import deprecated
from cocotb._py_compat import Self, cached_property
from cocotb._utils import pointer_str


class Trigger:
    """A future event that a Task can wait upon."""

    def __init__(self) -> None:
        self._primed = False

    @cached_property
    def _log(self) -> logging.Logger:
        return logging.getLogger(f"cocotb.{type(self).__qualname__}.0x{id(self):x}")

    def _prime(self, callback: Callable[["Self"], None]) -> None:
        """Set a callback to be invoked when the trigger fires.

        The callback will be invoked with a single argument, `self`.

        Sub-classes must override this, but should end by calling the base class
        method.

        .. warning::
            Do not call this directly within a :term:`task`. It is intended to be used
            only by the scheduler.
        """
        # Set _primed so the trigger can test if it's already been primed and behave appropriately.
        self._primed = True

    def _unprime(self) -> None:
        """Remove the callback, and perform cleanup if necessary.

        After being un-primed, a Trigger may be re-primed again in the future.
        Calling `_unprime` multiple times is allowed, subsequent calls should be
        a no-op.

        Sub-classes may override this, but should end by calling the base class
        method.

        .. warning::
            Do not call this directly within a :term:`task`. It is intended to be used
            only by the scheduler.
        """
        self._cleanup()

    def _cleanup(self) -> None:
        # Clear _primed so this Trigger can be re-primed.
        self._primed = False

    def __await__(self) -> Generator["Self", None, "Self"]:
        yield self
        return self


class _Event(Trigger):
    """Unique instance used by the Event object.

    One created for each attempt to wait on the event so that the scheduler
    can maintain a unique mapping of triggers to tasks.
    """

    _callback: Callable[["_Event"], None]

    def __init__(self, parent: "Event") -> None:
        super().__init__()
        self._parent = parent

    def _prime(self, callback: Callable[["_Event"], None]) -> None:
        if self._primed:
            return
        if self._parent.is_set():
            # If the event is already set, we need to call the callback
            # immediately, so we don't need to wait for the scheduler.
            callback(self)
            return
        self._callback = callback
        return super()._prime(callback)

    def _unprime(self) -> None:
        if not self._primed:
            return
        return super()._unprime()

    def _set(self) -> None:
        if self._primed:
            self._callback(self)

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

    def __init__(self, name: Optional[str] = None) -> None:
        self._event: _Event = _Event(self)
        self._name: Union[str, None] = None
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
    def name(self) -> Union[str, None]:
        """Name of the Event.

        .. deprecated:: 2.0
            The *name* field will be removed in a future release.
        """
        return self._name

    @name.setter
    @deprecated("The 'name' field will be removed in a future release.")
    def name(self, new_name: Union[str, None]) -> None:
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

    def set(self, data: Optional[object] = None) -> None:
        """Set the Event and unblock all Tasks blocked on this Event."""
        self._fired = True
        if data is not None:
            warnings.warn(
                "The data field will be removed in a future release.",
                DeprecationWarning,
                stacklevel=2,
            )
        self._data = data
        self._event._set()

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
        self._callback: Optional[Callable[[_InternalEvent], None]] = None
        self.fired: bool = False

    def _prime(self, callback: Callable[["_InternalEvent"], None]) -> None:
        if self._primed:
            raise RuntimeError("This Trigger may only be awaited once")
        self._callback = callback
        super()._prime(callback)
        if self.fired:
            self._callback(self)

    def _cleanup(self) -> None:
        # Don't clear _primed so a second call to _prime() fails.
        pass

    def set(self) -> None:
        """Wake up coroutine blocked on this event."""
        self.fired = True

        if self._callback is not None:
            self._callback(self)

    def is_set(self) -> bool:
        """Return true if event has been set."""
        return self.fired

    def __await__(
        self,
    ) -> Generator["Self", None, "Self"]:
        if self._primed:
            raise RuntimeError("Only one Task may await this Trigger")
        yield self
        return self

    def __repr__(self) -> str:
        return repr(self._parent)


class _Lock(Trigger):
    """Unique instance used by the Lock object.

    One created for each attempt to acquire the Lock so that the scheduler
    can maintain a unique mapping of triggers to tasks.
    """

    def __init__(self, parent: "Lock") -> None:
        super().__init__()
        self._parent = parent

    def _prime(self, callback: Callable[["Self"], None]) -> None:
        if self._primed:
            raise RuntimeError(
                "Lock.acquire() result can only be used by one task at a time"
            )
        self._callback = callback
        self._parent._prime_lock(self)
        return super()._prime(callback)

    def _unprime(self) -> None:
        if not self._primed:
            return
        self._parent._unprime_lock(self)
        return super()._unprime()

    def __repr__(self) -> str:
        return f"<{self._parent!r}.acquire() at {pointer_str(self)}>"


class Lock(AsyncContextManager[None]):
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

    def __init__(self, name: Optional[str] = None) -> None:
        self._pending_primed: List[_Lock] = []
        self._name: Union[str, None] = None
        if name is not None:
            warnings.warn(
                "The 'name' argument will be removed in a future release.",
                DeprecationWarning,
                stacklevel=2,
            )
            self._name = name
        self._locked: bool = False

    @property
    @deprecated("The 'name' field will be removed in a future release.")
    def name(self) -> Union[str, None]:
        """Name of the Lock.

        .. deprecated:: 2.0
            The *name* field will be removed in a future release.
        """
        return self._name

    @name.setter
    @deprecated("The 'name' field will be removed in a future release.")
    def name(self, new_name: Union[str, None]) -> None:
        self._name = new_name

    def locked(self) -> bool:
        """Return ``True`` if the lock has been acquired.

        .. versionchanged:: 2.0
            This is now a method to match :meth:`asyncio.Lock.locked`, rather than an attribute.
        """
        return self._locked

    def _acquire_and_fire(self, lock: _Lock) -> None:
        self._locked = True
        lock._callback(lock)

    def _prime_lock(self, lock: _Lock) -> None:
        if not self._locked:
            self._acquire_and_fire(lock)
        else:
            self._pending_primed.append(lock)

    def _unprime_lock(self, lock: _Lock) -> None:
        if lock in self._pending_primed:
            self._pending_primed.remove(lock)

    def acquire(self) -> Trigger:
        """Produce a trigger which fires when the lock is acquired."""
        trig = _Lock(self)
        return trig

    def release(self) -> None:
        """Release the lock."""
        if not self._locked:
            raise RuntimeError(f"Attempt to release an unacquired Lock {self!s}")

        self._locked = False

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

    def __init__(self, name: Optional[str] = None) -> None:
        super().__init__()
        self.name = name

    def _prime(self, callback: Callable[["Self"], None]) -> None:
        if self._primed:
            return
        callback(self)
        return super()._prime(callback)

    def __repr__(self) -> str:
        if self.name is None:
            fmt = "<{0} at {2}>"
        else:
            fmt = "<{0} for {1} at {2}>"
        return fmt.format(type(self).__qualname__, self.name, pointer_str(self))
