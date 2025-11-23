from __future__ import annotations

import sys
from asyncio import CancelledError
from typing import TYPE_CHECKING

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
async def test_TaskManager_basic(_: object) -> None:
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
                raise
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
async def test_TaskManager_start_soon_after_cancel(_: object) -> None:
    try:
        async with TaskManager() as tm:
            task = tm.start_soon(raises_after(1))

            try:
                await task
            finally:
                tm.start_soon(coro(2))

    except BaseExceptionGroup as e:
        runtime_error, rest = e.split(RuntimeError)
        assert runtime_error is not None
        assert len(runtime_error.exceptions) == 1
        assert rest is not None
        my_exc, rest = rest.split(MyException)
        assert my_exc is not None
        assert len(my_exc.exceptions) == 1
        assert rest is None


@cocotb.test
async def test_cancel_in_aexit_with_nested(_: object) -> None:
    cancelled = False
    e = Event()

    async with TaskManager() as a:

        @a.fork
        async def do_stuff() -> None:
            async with TaskManager() as b:

                @b.fork
                async def gets_cancelled() -> None:
                    try:
                        await e.wait()
                    finally:
                        nonlocal cancelled
                        cancelled = True

        # wait until do_stuff's TaskManager is in __aexit__
        await Timer(1)

        # cancel do_stuff to see what happens when a TaskManager is cancelled when
        # waiting for finish in __aexit__
        do_stuff.cancel()

    # ensure do_stuff's children are also cancelled
    assert cancelled
