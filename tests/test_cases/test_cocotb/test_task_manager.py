# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import sys
from asyncio import CancelledError
from typing import TYPE_CHECKING

import pytest

import cocotb
from cocotb.triggers import Event, TaskManager, Timer, Trigger

if TYPE_CHECKING:
    from collections.abc import Generator

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup


async def coro(wait: int, ret: int = 0) -> int:
    await Timer(wait)
    return ret


class AwaitableThing:
    def __init__(self, wait: int, ret: int = 0) -> None:
        self._wait = wait
        self._ret = ret

    def __await__(self) -> Generator[Trigger, None, int]:
        yield from coro(self._wait).__await__()
        return self._ret


class MyException(Exception): ...


async def raises_after(wait: int) -> None:
    await Timer(wait)
    raise MyException()


@cocotb.test
async def test_TaskManager_passes(_: object) -> None:
    timer = Timer(2)

    async with TaskManager() as tm:
        task1 = tm.start_soon(timer)
        task2 = tm.start_soon(AwaitableThing(3, ret=123))
        task3 = tm.start_soon(coro(4, ret=456))

        @tm.fork
        async def task4() -> int:
            await Timer(5)
            return 789

    assert task1.done()
    assert task1.result() == timer
    assert task2.done()
    assert task2.result() == 123
    assert task3.done()
    assert task3.result() == 456
    assert task4.done()
    assert task4.result() == 789


@cocotb.test
async def test_TaskManager_no_tasks_passes(_: object) -> None:
    async with TaskManager():
        pass


@cocotb.test
async def test_TaskManager_failure_in_block(_: object) -> None:
    try:
        async with TaskManager() as tm:

            @tm.fork
            async def stuff() -> int:
                await Timer(5)
                return 789

            raise MyException()

    except BaseExceptionGroup as e:
        my_exc, rest = e.split(MyException)
        assert rest is None
        assert my_exc is not None
        assert len(my_exc.exceptions) == 1

    assert stuff.cancelled()


@cocotb.test
async def test_TaskManager_child_failure_in_block(_: object) -> None:
    try:
        async with TaskManager() as tm:
            tm.start_soon(raises_after(1))

            @tm.fork
            async def stuff() -> int:
                await Timer(5)
                return 789

            try:
                await Timer(5)
            except CancelledError:
                raise  # can't use pytest.raises as that causes CancelledError to be swallowed
            else:
                assert False, "Didn't see CancelledError"

    except BaseExceptionGroup as e:
        my_exc, rest = e.split(MyException)
        assert rest is None
        assert my_exc is not None
        assert len(my_exc.exceptions) == 1

    assert stuff.cancelled()


@cocotb.test
async def test_TaskManager_child_failure_in_exit(_: object) -> None:
    try:
        async with TaskManager() as tm:
            tm.start_soon(raises_after(2))

            @tm.fork
            async def stuff() -> int:
                await Timer(5)
                return 789

    except BaseExceptionGroup as e:
        my_exc, rest = e.split(MyException)
        assert rest is None
        assert my_exc is not None
        assert len(my_exc.exceptions) == 1

    assert stuff.cancelled()


@cocotb.test
async def test_TaskManager_external_cancel_in_block(_: object) -> None:
    cancelled = False
    e = Event()

    async def do_stuff() -> None:
        async with TaskManager():
            try:
                await e.wait()
            finally:
                nonlocal cancelled
                cancelled = True

    task = cocotb.start_soon(do_stuff())

    # wait until do_stuff's TaskManager is blocking
    await Timer(1)

    # cancel do_stuff externally
    task.cancel()
    await task.complete

    # ensure do_stuff's children are also cancelled
    assert cancelled


@cocotb.test
async def test_TaskManager_external_cancel_in_block_ignored_at_end_of_block(
    _: object,
) -> None:
    async def do_stuff() -> None:
        async with TaskManager():
            try:
                await Timer(2)
            except CancelledError:
                pass

    task = cocotb.start_soon(do_stuff())

    # wait until do_stuff's TaskManager is blocking
    await Timer(1)

    # cancel do_stuff externally
    task.cancel()
    await task.complete
    assert not task.cancelled()
    assert task.exception() is not None


@cocotb.test
async def test_TaskManager_external_cancel_in_block_ignored_new_raise(
    _: object,
) -> None:
    async def do_stuff() -> None:
        async with TaskManager():
            try:
                await Timer(2)
            except CancelledError:
                raise MyException()

    task = cocotb.start_soon(do_stuff())

    # wait until do_stuff's TaskManager is blocking
    await Timer(1)

    # cancel do_stuff externally
    task.cancel()
    await task.complete
    assert not task.cancelled()
    assert task.exception() is not None


@cocotb.test
async def test_TaskManager_external_cancel_in_block_ignored_and_await(
    _: object,
) -> None:
    async def do_stuff() -> None:
        async with TaskManager():
            try:
                await Timer(2)
            except CancelledError:
                pass

            await Timer(1)

    task = cocotb.start_soon(do_stuff())

    # wait until do_stuff's TaskManager is blocking
    await Timer(1)

    # cancel do_stuff externally
    task.cancel()
    await task.complete
    assert not task.cancelled()
    assert task.exception() is not None


@cocotb.test
async def test_TaskManager_external_cancel_in_aexit(_: object) -> None:
    cancelled = False
    e = Event()

    async def do_stuff() -> None:
        async with TaskManager() as tm:

            @tm.fork
            async def do_stuff() -> None:
                try:
                    await e.wait()
                finally:
                    nonlocal cancelled
                    cancelled = True

    task = cocotb.start_soon(do_stuff())

    # wait until do_stuff's TaskManager is in __aexit__
    await Timer(1)

    # cancel do_stuff to see what happens when a TaskManager is cancelled when
    # waiting for finish in __aexit__
    task.cancel()
    await task.complete

    # ensure do_stuff's children are also cancelled
    assert cancelled


@cocotb.test
@cocotb.xfail(raises=RuntimeError, reason="Ignored CancelledError")
async def test_TaskManager_child_fails_ignore_cancel_at_end_of_block(_: object) -> None:
    async with TaskManager() as tm:
        tm.start_soon(raises_after(1))

        try:
            await Timer(2)
        except CancelledError:
            pass

    await Timer(1)


@cocotb.test
@cocotb.xfail(raises=RuntimeError, reason="Ignored CancelledError")
async def test_TaskManager_child_fails_ignore_cancel_and_await(_: object) -> None:
    async with TaskManager() as tm:
        tm.start_soon(raises_after(1))

        try:
            await Timer(2)
        except CancelledError:
            pass

        await Timer(1)


@cocotb.test
@cocotb.xfail(raises=RuntimeError, reason="Ignored CancelledError")
async def test_TaskManager_child_fails_ignore_cancel_new_raise(_: object) -> None:
    async with TaskManager() as tm:
        tm.start_soon(raises_after(1))

        try:
            await Timer(2)
        except CancelledError:
            raise MyException()


@cocotb.test
async def test_TaskManager_reused_context(_: object) -> None:
    tm = TaskManager()

    async with tm:
        tm.start_soon(coro(1))

    with pytest.raises(RuntimeError):
        async with tm:
            pass


@cocotb.test
async def test_TaskManager_start_soon_after_cancel(_: object) -> None:
    try:
        async with TaskManager() as tm:
            task = tm.start_soon(raises_after(1))

            try:
                await task
            finally:
                c = coro(2)
                with pytest.raises(RuntimeError):
                    tm.start_soon(c)
                c.close()  # avoid ResourceWarning since we didn't await it.

    except BaseExceptionGroup as e:
        my_exc, rest = e.split(MyException)
        assert my_exc is not None
        assert len(my_exc.exceptions) == 1
        assert rest is None


@cocotb.test
async def test_TaskManager_start_soon_after_finished(_: object) -> None:
    async with TaskManager() as tm:
        tm.start_soon(coro(1))

    c = coro(1)
    with pytest.raises(RuntimeError):
        tm.start_soon(c)
    c.close()  # avoid ResourceWarning since we didn't await it.


@cocotb.test
async def test_TaskManager_cancel_child_task_in_block(_: object) -> None:
    cancelled = False

    async def child() -> None:
        try:
            await Timer(5)
        finally:
            nonlocal cancelled
            cancelled = True

    async with TaskManager() as tm:
        task = tm.start_soon(child())

        await Timer(1)
        task.cancel()

    assert cancelled


@cocotb.test
async def test_TaskManager_KeyboardInterrupt_in_block(_: object) -> None:
    with pytest.raises(KeyboardInterrupt):
        async with TaskManager() as tm:
            tm.start_soon(coro(5))

            await Timer(1)
            raise KeyboardInterrupt()


# Can't test KeyboardInterrupt in child Task since that will take a path to shut down
# the simulation.


@cocotb.test
async def test_TaskManager_child_and_nested_fails_simultaneously(_: object) -> None:
    try:
        async with TaskManager() as tm:

            @tm.fork
            async def outer() -> None:
                await Timer(1)
                raise MyException()

            async with TaskManager():
                await Timer(2)

    except BaseExceptionGroup as e:
        my_exc, rest = e.split(MyException)
        assert rest is None
        assert my_exc is not None
        assert len(my_exc.exceptions) == 1


@cocotb.test
async def test_TaskManager_nested_failures(_: object) -> None:
    try:
        async with TaskManager() as tm:

            @tm.fork
            async def outer() -> None:
                await Timer(2)

            async with TaskManager():

                @tm.fork
                async def inner() -> None:
                    await Timer(1)
                    raise MyException("inner")

    except BaseExceptionGroup as e:
        my_exc, rest = e.split(MyException)
        assert rest is None
        assert my_exc is not None
        assert len(my_exc.exceptions) == 1


# @cocotb.test
# async def test_TaskManager_nested_cancel_in_block(_: object) -> None:
#     cancelled_inner_tm = False
#     cancelled_outer_task = False
#     e = Event()

#     async def do_stuff() -> None:
#         async with TaskManager() as tm:

#             @tm.fork
#             async def outer() -> None:
#                 try:
#                     await e.wait()
#                 finally:
#                     nonlocal cancelled_outer_task
#                     cancelled_outer_task = True

#             async with TaskManager():
#                 try:
#                     await e.wait()
#                 finally:
#                     nonlocal cancelled_inner_tm
#                     cancelled_inner_tm = True

#     task = cocotb.start_soon(do_stuff())

#     # wait until do_stuff's TaskManager is blocking
#     await Timer(1)

#     # cancel do_stuff to see what happens when a TaskManager is cancelled when
#     # waiting for finish in __aexit__
#     task.cancel()

#     # ensure do_stuff's children are also cancelled
#     assert cancelled_inner_tm
#     assert cancelled_outer_task


# @cocotb.test
# async def test_TaskManager_nested_cancel_in_aexit(_: object) -> None:
#     cancelled_inner_task = False
#     cancelled_outer_task = False
#     e = Event()

#     async def do_stuff() -> None:
#         async with TaskManager() as tm:

#             @tm.fork
#             async def outer() -> None:
#                 try:
#                     await e.wait()
#                 finally:
#                     nonlocal cancelled_outer_task
#                     cancelled_outer_task = True

#             async with TaskManager():

#                 @tm.fork
#                 async def inner() -> None:
#                     try:
#                         await e.wait()
#                     finally:
#                         nonlocal cancelled_inner_task
#                         cancelled_inner_task = True

#     task = cocotb.start_soon(do_stuff())

#     # wait until do_stuff's TaskManager is in __aexit__
#     await Timer(1)

#     # cancel do_stuff to see what happens when a TaskManager is cancelled when
#     # waiting for finish in __aexit__
#     task.cancel()

#     # ensure do_stuff's children are also cancelled
#     assert cancelled_inner_task
#     assert cancelled_outer_task
