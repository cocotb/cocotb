# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import asyncio.queues
import collections
import heapq
from abc import abstractmethod
from typing import (
    Deque,
    Generic,
    List,
    Tuple,
    TypeVar,
)

import cocotb
from cocotb._utils import pointer_str
from cocotb.task import Task
from cocotb.triggers import Event

__all__ = (
    "AbstractQueue",
    "LifoQueue",
    "PriorityQueue",
    "Queue",
    "QueueEmpty",
    "QueueFull",
)


class QueueFull(asyncio.queues.QueueFull):
    """Raised when the :meth:`Queue.put_nowait()` method is called on a full :class:`Queue`."""


class QueueEmpty(asyncio.queues.QueueEmpty):
    """Raised when the :meth:`Queue.get_nowait()` method is called on an empty :class:`Queue`."""


T = TypeVar("T")


class AbstractQueue(Generic[T]):
    """A queue, useful for coordinating producer and consumer coroutines.

    If *maxsize* is less than or equal to 0, the queue size is infinite. If it
    is an integer greater than 0, then :meth:`put` will block when the queue
    reaches *maxsize*, until an item is removed by :meth:`get`.
    """

    def __init__(self, maxsize: int = 0) -> None:
        self._maxsize: int = maxsize
        self._getters: Deque[Tuple[Event, Task[object]]] = collections.deque()
        self._putters: Deque[Tuple[Event, Task[object]]] = collections.deque()

    @abstractmethod
    def _get(self) -> T:
        """Remove and return the next element from the queue."""

    @abstractmethod
    def _put(self, item: T) -> None:
        """Place a new element on the queue."""

    @abstractmethod
    def _size(self) -> int:
        """Return the number of elements in the queue."""

    @abstractmethod
    def _repr(self) -> str:
        """Return a string representation of the state of the queue."""

    def _wakeup_next(self, waiters: Deque[Tuple[Event, Task[object]]]) -> None:
        while waiters:
            event, task = waiters.popleft()
            if not task.done():
                event.set()
                break

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self._format()} at {pointer_str(self)}>"

    def __str__(self) -> str:
        return f"<{type(self).__name__} {self._format()}>"

    def _format(self) -> str:
        result = f"maxsize={self._maxsize!r}"
        if getattr(self, "_queue", None):
            result += f" _queue={self._repr()}"
        if self._getters:
            result += f" _getters[{len(self._getters)}]"
        if self._putters:
            result += f" _putters[{len(self._putters)}]"
        return result

    def qsize(self) -> int:
        """Number of items in the queue."""
        return self._size()

    @property
    def maxsize(self) -> int:
        """Number of items allowed in the queue."""
        return self._maxsize

    def empty(self) -> bool:
        """Return ``True`` if the queue is empty, ``False`` otherwise."""
        return self._size() == 0

    def full(self) -> bool:
        """Return ``True`` if there are :meth:`maxsize` items in the queue.

        .. note::
            If the Queue was initialized with ``maxsize=0`` (the default), then
            :meth:`full` is never ``True``.
        """
        if self._maxsize <= 0:
            return False
        else:
            return self.qsize() >= self._maxsize

    async def put(self, item: T) -> None:
        """Put an *item* into the queue.

        If the queue is full, wait until a free
        slot is available before adding the item.
        """
        while self.full():
            event = Event()
            self._putters.append((event, cocotb.task.current_task()))
            await event.wait()
        self.put_nowait(item)

    def put_nowait(self, item: T) -> None:
        """Put an *item* into the queue without blocking.

        If no free slot is immediately available, raise :exc:`~cocotb.queue.QueueFull`.
        """
        if self.full():
            raise QueueFull()
        self._put(item)
        self._wakeup_next(self._getters)

    async def get(self) -> T:
        """Remove and return an item from the queue.

        If the queue is empty, wait until an item is available.
        """
        while self.empty():
            event = Event()
            self._getters.append((event, cocotb.task.current_task()))
            await event.wait()
        return self.get_nowait()

    def get_nowait(self) -> T:
        """Remove and return an item from the queue.

        Return an item if one is immediately available, else raise
        :exc:`~cocotb.queue.QueueEmpty`.
        """
        if self.empty():
            raise QueueEmpty()
        item = self._get()
        self._wakeup_next(self._putters)
        return item


class Queue(AbstractQueue[T]):
    """A subclass of :class:`AbstractQueue`; retrieves oldest entries first (FIFO)."""

    def __init__(self, maxsize: int = 0) -> None:
        super().__init__(maxsize)
        self._queue: Deque[T] = collections.deque()

    def _put(self, item: T) -> None:
        self._queue.append(item)

    def _get(self) -> T:
        return self._queue.popleft()

    def _size(self) -> int:
        return len(self._queue)

    def _repr(self) -> str:
        return repr(self._queue)


class PriorityQueue(AbstractQueue[T]):
    r"""A subclass of :class:`AbstractQueue`; retrieves entries in priority order (smallest item first).

    Entries are typically tuples of the form ``(priority number, data)``.
    """

    def __init__(self, maxsize: int = 0) -> None:
        super().__init__(maxsize)
        self._queue: List[T] = []

    def _put(self, item: T) -> None:
        heapq.heappush(self._queue, item)

    def _get(self) -> T:
        return heapq.heappop(self._queue)

    def _size(self) -> int:
        return len(self._queue)

    def _repr(self) -> str:
        return repr(self._queue)


class LifoQueue(AbstractQueue[T]):
    """A subclass of :class:`AbstractQueue`; retrieves most recently added entries first (LIFO)."""

    def __init__(self, maxsize: int = 0) -> None:
        super().__init__(maxsize)
        self._queue: Deque[T] = collections.deque()

    def _put(self, item: T) -> None:
        self._queue.append(item)

    def _get(self) -> T:
        return self._queue.pop()

    def _size(self) -> int:
        return len(self._queue)

    def _repr(self) -> str:
        return repr(self._queue)
