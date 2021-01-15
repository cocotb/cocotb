# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import collections
import heapq
from asyncio import QueueEmpty, QueueFull

import cocotb
from cocotb.triggers import Event


class Queue:
    def __init__(self, maxsize=0):

        self._maxsize = maxsize

        self._finished = Event()
        self._finished.set()

        self._getters = collections.deque()
        self._putters = collections.deque()

        self._unfinished_tasks = 0

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
            if not task._finished:
                event.set()
                break

    def __repr__(self):
        return '<{} at {:#x} {}>'.format(type(self).__name__, id(self), self._format())

    def __str__(self):
        return '<{} {}>'.format(type(self).__name__, self._format())

    def __class_getitem__(cls, type):
        return cls

    def _format(self):
        result = 'maxsize={}'.format(repr(self._maxsize))
        if getattr(self, '_queue', None):
            result += ' _queue={}'.format(repr(list(self._queue)))
        if self._getters:
            result += ' _getters[{}]'.format(len(self._getters))
        if self._putters:
            result += ' _putters[{}]'.format(len(self._putters))
        if self._unfinished_tasks:
            result += ' tasks={}'.format(self._unfinished_tasks)
        return result

    def qsize(self):
        return len(self._queue)

    @property
    def maxsize(self):
        return self._maxsize

    def empty(self):
        return not self._queue

    def full(self):
        if self._maxsize <= 0:
            return False
        else:
            return self.qsize() >= self._maxsize

    async def put(self, item):
        while self.full():
            event = Event('{} put'.format(type(self).__name__))
            self._putters.append((event, cocotb.scheduler._current_task))
            await event.wait()
        self.put_nowait(item)

    def put_nowait(self, item):
        if self.full():
            raise QueueFull()
        self._put(item)
        self._unfinished_tasks += 1
        self._finished.clear()
        self._wakeup_next(self._getters)

    async def get(self):
        while self.empty():
            event = Event('{} get'.format(type(self).__name__))
            self._getters.append((event, cocotb.scheduler._current_task))
            await event.wait()
        return self.get_nowait()

    def get_nowait(self):
        if self.empty():
            raise QueueEmpty()
        item = self._get()
        self._wakeup_next(self._putters)
        return item

    def task_done(self):
        if self._unfinished_tasks <= 0:
            raise ValueError("task_done() called with no outstanding tasks")
        self._unfinished_tasks -= 1
        if self._unfinished_tasks == 0:
            self._finished.set()

    async def join(self):
        if self._unfinished_tasks > 0:
            await self._finished.wait()


class PriorityQueue(Queue):
    """A subclass of Queue; retrieves entries in priority order (smallest item first).

    Entries are typically tuples of the form: (priority number, data).
    """

    def _init(self, maxsize):
        self._queue = []

    def _put(self, item):
        heapq.heappush(self._queue, item)

    def _get(self):
        return heapq.heappop(self._queue)


class LifoQueue(Queue):
    """A subclass of Queue; retrieves most recently added entries first."""

    def _init(self, maxsize):
        self._queue = collections.deque()

    def _put(self, item):
        self._queue.append(item)

    def _get(self):
        return self._queue.pop()
