# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import asyncio.queues
import collections
import heapq
from typing import Generic, TypeVar

import cocotb
from cocotb.triggers import Event, _pointer_str


class QueueFull(asyncio.queues.QueueFull):
    """Raised when the Queue.put_nowait() method is called on a full Queue."""


class QueueEmpty(asyncio.queues.QueueEmpty):
    """Raised when the Queue.get_nowait() method is called on a empty Queue."""


T = TypeVar("T")


class Queue(Generic[T]):
    """A queue, useful for coordinating producer and consumer coroutines.

    If *maxsize* is less than or equal to 0, the queue size is infinite. If it
    is an integer greater than 0, then :meth:`put` will block when the queue
    reaches *maxsize*, until an item is removed by :meth:`get`.
    """

    def __init__(self, maxsize: int = 0):

        self._maxsize = maxsize

        self._finished = Event()
        self._finished.set()

        self._getters = collections.deque()
        self._putters = collections.deque()

        self._init(maxsize)

    def _init(self, maxsize):
        self._queue = collections.deque()

    def _put(self, item):
        self._queue.append(item)

    def _get(self):
        return self._queue.popleft()

    def _wakeup_next(self, waiters):
        while waiters:
            event, task = waiters.popleft()
            if not task.done():
                event.set()
                break

    def __repr__(self):
        return "<{} {} at {}>".format(
            type(self).__name__, self._format(), _pointer_str(self)
        )

    def __str__(self):
        return "<{} {}>".format(type(self).__name__, self._format())

    def __class_getitem__(cls, type):
        return cls

    def _format(self):
        result = "maxsize={}".format(repr(self._maxsize))
        if getattr(self, "_queue", None):
            result += " _queue={}".format(repr(list(self._queue)))
        if self._getters:
            result += " _getters[{}]".format(len(self._getters))
        if self._putters:
            result += " _putters[{}]".format(len(self._putters))
        return result

    def qsize(self) -> int:
        """Number of items in the queue."""
        return len(self._queue)

    @property
    def maxsize(self) -> int:
        """Number of items allowed in the queue."""
        return self._maxsize

    def empty(self) -> bool:
        """Return ``True`` if the queue is empty, ``False`` otherwise."""
        return not self._queue

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
            event = Event("{} put".format(type(self).__name__))
            self._putters.append((event, cocotb.scheduler._current_task))
            await event.wait()
        self.put_nowait(item)

    def put_nowait(self, item: T) -> None:
        """Put an *item* into the queue without blocking.

        If no free slot is immediately available, raise :exc:`asyncio.QueueFull`.
        """
        if self.full():
            raise QueueFull()
        self._put(item)
        self._finished.clear()
        self._wakeup_next(self._getters)

    async def get(self) -> T:
        """Remove and return an item from the queue.

        If the queue is empty, wait until an item is available.
        """
        while self.empty():
            event = Event("{} get".format(type(self).__name__))
            self._getters.append((event, cocotb.scheduler._current_task))
            await event.wait()
        return self.get_nowait()

    def get_nowait(self) -> T:
        """Remove and return an item from the queue.

        Return an item if one is immediately available, else raise
        :exc:`asyncio.QueueEmpty`.
        """
        if self.empty():
            raise QueueEmpty()
        item = self._get()
        self._wakeup_next(self._putters)
        return item


class PriorityQueue(Queue):
    r"""A subclass of :class:`Queue`; retrieves entries in priority order (smallest item first).

    Entries are typically tuples of the form ``(priority number, data)``.
    """

    def _init(self, maxsize):
        self._queue = []

    def _put(self, item):
        heapq.heappush(self._queue, item)

    def _get(self):
        return heapq.heappop(self._queue)


class LifoQueue(Queue):
    """A subclass of :class:`Queue`; retrieves most recently added entries first."""

    def _init(self, maxsize):
        self._queue = collections.deque()

    def _put(self, item):
        self._queue.append(item)

    def _get(self):
        return self._queue.pop()
