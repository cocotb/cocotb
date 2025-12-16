# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import sys
from asyncio import CancelledError
from typing import TYPE_CHECKING, Any

import pytest
from common import assert_takes

import cocotb
from cocotb.task import Task
from cocotb.triggers import Event, NullTrigger, TaskManager, Timer, Trigger

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
@cocotb.parametrize(continue_on_error=[True, False])
async def test_passes(_: object, continue_on_error: bool) -> None:
    timer = Timer(2)

    with assert_takes(5, "step"):
        async with TaskManager(continue_on_error=continue_on_error) as tm:
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
@cocotb.parametrize(continue_on_error=[True, False])
async def test_no_tasks_passes(_: object, continue_on_error: bool) -> None:
    async with TaskManager(continue_on_error=continue_on_error):
        pass


@cocotb.test
@cocotb.parametrize(inner_continue_on_error=[True, False])
@cocotb.parametrize(outer_continue_on_error=[True, False])
async def test_nested_passes(
    _: object, inner_continue_on_error: bool, outer_continue_on_error: bool
) -> None:
    timer = Timer(2)

    with assert_takes(8, "step"):
        async with TaskManager(continue_on_error=outer_continue_on_error) as tm_outer:
            task_outer = tm_outer.start_soon(coro(8, ret=808))

            with assert_takes(5, "step"):
                async with TaskManager(
                    continue_on_error=inner_continue_on_error
                ) as tm_inner:
                    task1 = tm_inner.start_soon(timer)
                    task2 = tm_inner.start_soon(AwaitableThing(3, ret=123))
                    task3 = tm_inner.start_soon(coro(4, ret=456))

                    @tm_inner.fork
                    async def task4() -> int:
                        await Timer(5)
                        return 789

    assert task_outer.result() == 808
    assert task1.result() == timer
    assert task2.result() == 123
    assert task3.result() == 456
    assert task4.result() == 789


@cocotb.test
@cocotb.parametrize(inner_continue_on_error=[True, False])
@cocotb.parametrize(outer_continue_on_error=[True, False])
async def test_nested_in_child_passes(
    _: object, inner_continue_on_error: bool, outer_continue_on_error: bool
) -> None:
    timer = Timer(2)

    task1: Task[Any] | None = None
    task2: Task[Any] | None = None
    task3: Task[Any] | None = None
    task4: Task[Any] | None = None

    async with TaskManager(continue_on_error=outer_continue_on_error) as tm_outer:
        task_outer = tm_outer.start_soon(coro(5, ret=808))

        @tm_outer.fork
        async def outer_task() -> None:
            async with TaskManager(
                continue_on_error=inner_continue_on_error
            ) as tm_inner:
                nonlocal task1, task2, task3, task4

                task1 = tm_inner.start_soon(timer)
                task2 = tm_inner.start_soon(AwaitableThing(3, ret=123))
                task3 = tm_inner.start_soon(coro(4, ret=456))

                @tm_inner.fork
                async def task4() -> int:
                    await Timer(5)
                    return 789

    assert task_outer.result() == 808
    assert task1 is not None
    assert task2 is not None
    assert task3 is not None
    assert task4 is not None
    assert task1.result() == timer
    assert task2.result() == 123
    assert task3.result() == 456
    assert task4.result() == 789


@cocotb.test
@cocotb.parametrize(continue_on_error=[True, False])
async def test_failure_in_block(_: object, continue_on_error: bool) -> None:
    try:
        async with TaskManager(continue_on_error=continue_on_error) as tm:
            task = tm.start_soon(coro(3, ret=789))
            raise MyException()

    except BaseExceptionGroup as e:
        my_exc, rest = e.split(MyException)
        assert rest is None
        assert my_exc is not None
        assert len(my_exc.exceptions) == 1

    if continue_on_error:
        assert task.result() == 789
    else:
        assert task.cancelled()


@cocotb.test
@cocotb.parametrize(outer_continue_on_error=[True, False])
@cocotb.parametrize(inner_continue_on_error=[True, False])
async def test_failure_in_nested_block(
    _: object, outer_continue_on_error: bool, inner_continue_on_error: bool
) -> None:
    try:
        async with TaskManager(continue_on_error=outer_continue_on_error) as tm_outer:
            task_outer = tm_outer.start_soon(coro(5, ret=9))

            async with TaskManager(
                continue_on_error=inner_continue_on_error
            ) as tm_inner:
                task_inner = tm_inner.start_soon(coro(3, ret=789))
                raise MyException()

    except BaseExceptionGroup as e:
        my_exc, rest = e.split(MyException)
        assert rest is None
        assert my_exc is not None
        assert len(my_exc.exceptions) == 1

    if outer_continue_on_error:
        assert task_outer.result() == 9
    else:
        assert task_outer.cancelled()

    if inner_continue_on_error:
        assert task_inner.result() == 789
    else:
        assert task_inner.cancelled()


@cocotb.test
@cocotb.parametrize(outer_continue_on_error=[True, False])
@cocotb.parametrize(inner_continue_on_error=[True, False])
async def test_failure_in_nested_child_block(
    _: object, outer_continue_on_error: bool, inner_continue_on_error: bool
) -> None:
    task_inner: Task[Any] | None = None

    try:
        async with TaskManager(continue_on_error=outer_continue_on_error) as tm_outer:
            task_outer = tm_outer.start_soon(coro(5, ret=9))

            @tm_outer.fork
            async def inner_block() -> None:
                async with TaskManager(
                    continue_on_error=inner_continue_on_error
                ) as tm_inner:
                    nonlocal task_inner
                    task_inner = tm_inner.start_soon(coro(3, ret=789))

                    raise MyException()

    except BaseExceptionGroup as e:
        my_exc, rest = e.split(MyException)
        assert rest is None
        assert my_exc is not None
        assert len(my_exc.exceptions) == 1

    if outer_continue_on_error:
        assert task_outer.result() == 9
    else:
        assert task_outer.cancelled()

    assert task_inner is not None
    if inner_continue_on_error:
        assert task_inner.result() == 789
    else:
        assert task_inner.cancelled()


@cocotb.test
@cocotb.parametrize(continue_on_error=[True, False])
async def test_child_failure_in_block(_: object, continue_on_error: bool) -> None:
    takes = 5 if continue_on_error else 1

    with assert_takes(takes, "step"):
        try:
            async with TaskManager(continue_on_error=continue_on_error) as tm:
                task_failure = tm.start_soon(raises_after(1))
                task = tm.start_soon(coro(3, ret=789))

                try:
                    await Timer(5)
                except CancelledError:
                    assert not continue_on_error
                    raise  # can't use pytest.raises as that causes CancelledError to be swallowed
                else:
                    assert continue_on_error

        except BaseExceptionGroup as e:
            my_exc, rest = e.split(MyException)
            assert rest is None
            assert my_exc is not None
            assert len(my_exc.exceptions) == 1

    assert task_failure.exception() is not None

    if continue_on_error:
        assert task.result() == 789
    else:
        assert task.cancelled()


@cocotb.test
@cocotb.parametrize(outer_continue_on_error=[True, False])
@cocotb.parametrize(inner_continue_on_error=[True, False])
async def test_child_failure_in_nested_block(
    _: object, outer_continue_on_error: bool, inner_continue_on_error: bool
) -> None:
    try:
        async with TaskManager(continue_on_error=outer_continue_on_error) as tm_outer:
            task_outer = tm_outer.start_soon(coro(5, ret=9))

            async with TaskManager(
                continue_on_error=inner_continue_on_error
            ) as tm_inner:
                task_inner_failure = tm_inner.start_soon(raises_after(1))
                task_inner = tm_inner.start_soon(coro(3, ret=789))

                try:
                    await Timer(4)
                except CancelledError:
                    assert not inner_continue_on_error
                    raise  # can't use pytest.raises as that causes CancelledError to be swallowed
                else:
                    assert inner_continue_on_error

    except BaseExceptionGroup as e:
        my_exc, rest = e.split(MyException)
        assert rest is None
        assert my_exc is not None
        assert len(my_exc.exceptions) == 1

    assert task_inner_failure.exception() is not None

    if outer_continue_on_error:
        assert task_outer.result() == 9
    else:
        assert task_outer.cancelled()

    if inner_continue_on_error:
        assert task_inner.result() == 789
    else:
        assert task_inner.cancelled()


@cocotb.test
@cocotb.parametrize(outer_continue_on_error=[True, False])
@cocotb.parametrize(inner_continue_on_error=[True, False])
async def test_child_failure_in_nested_child_block(
    _: object, outer_continue_on_error: bool, inner_continue_on_error: bool
) -> None:
    task_inner_failure: Task[Any] | None = None
    task_inner: Task[Any] | None = None

    try:
        async with TaskManager(continue_on_error=outer_continue_on_error) as tm_outer:
            task_outer = tm_outer.start_soon(coro(5, ret=9))

            @tm_outer.fork
            async def inner_block() -> None:
                async with TaskManager(
                    continue_on_error=inner_continue_on_error
                ) as tm_inner:
                    nonlocal task_inner_failure, task_inner
                    task_inner_failure = tm_inner.start_soon(raises_after(1))
                    task_inner = tm_inner.start_soon(coro(3, ret=789))

                    try:
                        await Timer(4)
                    except CancelledError:
                        assert not inner_continue_on_error
                        raise  # can't use pytest.raises as that causes CancelledError to be swallowed
                    else:
                        assert inner_continue_on_error

    except BaseExceptionGroup as e:
        my_exc, rest = e.split(MyException)
        assert rest is None
        assert my_exc is not None
        assert len(my_exc.exceptions) == 1

    assert task_inner_failure is not None
    assert task_inner_failure.exception() is not None

    if outer_continue_on_error:
        assert task_outer.result() == 9
    else:
        assert task_outer.cancelled()

    assert task_inner is not None
    if inner_continue_on_error:
        assert task_inner.result() == 789
    else:
        assert task_inner.cancelled()


@cocotb.test
@cocotb.parametrize(continue_on_error=[True, False])
async def test_child_failure_in_exit(_: object, continue_on_error: bool) -> None:
    takes = 3 if continue_on_error else 2

    with assert_takes(takes, "step"):
        try:
            async with TaskManager(continue_on_error=continue_on_error) as tm:
                task_failure = tm.start_soon(raises_after(2))
                task = tm.start_soon(coro(3, ret=789))

        except BaseExceptionGroup as e:
            my_exc, rest = e.split(MyException)
            assert rest is None
            assert my_exc is not None
            assert len(my_exc.exceptions) == 1

    assert task_failure.exception() is not None

    if continue_on_error:
        assert task.result() == 789
    else:
        assert task.cancelled()


@cocotb.test
@cocotb.parametrize(outer_continue_on_error=[True, False])
@cocotb.parametrize(inner_continue_on_error=[True, False])
async def test_child_failure_in_nested_exit(
    _: object, outer_continue_on_error: bool, inner_continue_on_error: bool
) -> None:
    try:
        async with TaskManager(continue_on_error=outer_continue_on_error) as tm_outer:
            task_outer = tm_outer.start_soon(coro(5, ret=9))

            async with TaskManager(
                continue_on_error=inner_continue_on_error
            ) as tm_inner:
                task_inner_failure = tm_inner.start_soon(raises_after(2))
                task_inner = tm_inner.start_soon(coro(3, ret=789))

    except BaseExceptionGroup as e:
        my_exc, rest = e.split(MyException)
        assert rest is None
        assert my_exc is not None
        assert len(my_exc.exceptions) == 1

    assert task_inner_failure.exception() is not None

    if outer_continue_on_error:
        assert task_outer.result() == 9
    else:
        assert task_outer.cancelled()

    if inner_continue_on_error:
        assert task_inner.result() == 789
    else:
        assert task_inner.cancelled()


@cocotb.test
@cocotb.parametrize(outer_continue_on_error=[True, False])
@cocotb.parametrize(inner_continue_on_error=[True, False])
async def test_child_failure_in_nested_child_exit(
    _: object, outer_continue_on_error: bool, inner_continue_on_error: bool
) -> None:
    task_inner_failure: Task[Any] | None = None
    task_inner: Task[Any] | None = None
    try:
        async with TaskManager(continue_on_error=outer_continue_on_error) as tm_outer:
            task_outer = tm_outer.start_soon(coro(5, ret=9))

            @tm_outer.fork
            async def inner_block() -> None:
                nonlocal task_inner_failure, task_inner
                async with TaskManager(
                    continue_on_error=inner_continue_on_error
                ) as tm_inner:
                    task_inner_failure = tm_inner.start_soon(raises_after(2))
                    task_inner = tm_inner.start_soon(coro(3, ret=789))

    except BaseExceptionGroup as e:
        my_exc, rest = e.split(MyException)
        assert rest is None
        assert my_exc is not None
        assert len(my_exc.exceptions) == 1

    assert task_inner_failure is not None
    assert task_inner_failure.exception() is not None

    if outer_continue_on_error:
        assert task_outer.result() == 9
    else:
        assert task_outer.cancelled()

    assert task_inner is not None
    if inner_continue_on_error:
        assert task_inner.result() == 789
    else:
        assert task_inner.cancelled()


@cocotb.test
@cocotb.parametrize(continue_on_error=[True, False])
async def test_external_cancel_in_block(_: object, continue_on_error: bool) -> None:
    cancelled = False
    e = Event()

    async def run_task_manager() -> None:
        async with TaskManager(continue_on_error=continue_on_error):
            try:
                await e.wait()
            finally:
                nonlocal cancelled
                cancelled = True

    task = cocotb.start_soon(run_task_manager())

    # wait until run_task_manager's TaskManager is blocking
    await Timer(1)

    # cancel run_task_manager externally
    task.cancel()
    await task.complete

    # ensure run_task_manager's children are also cancelled
    assert cancelled


@cocotb.test
@cocotb.parametrize(outer_continue_on_error=[True, False])
@cocotb.parametrize(inner_continue_on_error=[True, False])
async def test_external_cancel_in_nested_block(
    _: object, outer_continue_on_error: bool, inner_continue_on_error: bool
) -> None:
    cancelled = False
    e = Event()

    outer_task: Task[Any] | None = None

    async def run_task_manager() -> None:
        async with TaskManager(continue_on_error=outer_continue_on_error) as tm_outer:
            nonlocal outer_task
            outer_task = tm_outer.start_soon(coro(5, ret=9))

            async with TaskManager(continue_on_error=inner_continue_on_error):
                try:
                    await e.wait()
                finally:
                    nonlocal cancelled
                    cancelled = True

    task = cocotb.start_soon(run_task_manager())

    # wait until run_task_manager's TaskManager is blocking
    await Timer(1)

    # cancel run_task_manager externally
    task.cancel()
    await task.complete

    # ensure run_task_manager's children are also cancelled
    assert outer_task is not None
    assert outer_task.cancelled()
    assert cancelled


@cocotb.test
@cocotb.parametrize(outer_continue_on_error=[True, False])
@cocotb.parametrize(inner_continue_on_error=[True, False])
async def test_external_cancel_in_nested_child_block(
    _: object, outer_continue_on_error: bool, inner_continue_on_error: bool
) -> None:
    cancelled = False
    e = Event()

    outer_task: Task[Any] | None = None
    inner_block: Task[Any] | None = None

    async def run_task_manager() -> None:
        async with TaskManager(continue_on_error=outer_continue_on_error) as tm_outer:
            nonlocal outer_task, inner_block
            outer_task = tm_outer.start_soon(coro(5, ret=9))

            @tm_outer.fork
            async def inner_block() -> None:
                async with TaskManager(continue_on_error=inner_continue_on_error):
                    try:
                        await e.wait()
                    finally:
                        nonlocal cancelled
                        cancelled = True

    task = cocotb.start_soon(run_task_manager())

    # wait until run_task_manager's TaskManager is blocking
    await Timer(1)

    # cancel run_task_manager externally
    task.cancel()
    await task.complete

    # ensure run_task_manager's children are also cancelled
    assert cancelled
    assert inner_block is not None
    assert inner_block.cancelled()
    assert outer_task is not None
    assert outer_task.cancelled()


@cocotb.test
@cocotb.parametrize(continue_on_error=[True, False])
async def test_external_cancel_in_aexit(_: object, continue_on_error: bool) -> None:
    inner_task: Task[Any] | None = None

    async def run_task_manager() -> None:
        async with TaskManager(continue_on_error=continue_on_error) as tm:
            nonlocal inner_task
            inner_task = tm.start_soon(coro(5, ret=9))

    task = cocotb.start_soon(run_task_manager())

    # wait until run_task_manager's TaskManager is in __aexit__
    await Timer(1)

    # cancel run_task_manager to see what happens when a TaskManager is cancelled when
    # waiting for finish in __aexit__
    task.cancel()
    await task.complete

    # ensure run_task_manager's children are also cancelled
    assert inner_task is not None
    assert inner_task.cancelled()


@cocotb.test
@cocotb.parametrize(outer_continue_on_error=[True, False])
@cocotb.parametrize(inner_continue_on_error=[True, False])
async def test_external_cancel_in_nested_aexit(
    _: object, outer_continue_on_error: bool, inner_continue_on_error: bool
) -> None:
    outer_task: Task[Any] | None = None
    inner_task: Task[Any] | None = None

    async def run_task_manager() -> None:
        async with TaskManager(continue_on_error=outer_continue_on_error) as tm_outer:
            nonlocal outer_task
            outer_task = tm_outer.start_soon(coro(5, ret=9))

            async with TaskManager(
                continue_on_error=inner_continue_on_error
            ) as tm_inner:
                nonlocal inner_task
                inner_task = tm_inner.start_soon(coro(5, ret=9))

    task = cocotb.start_soon(run_task_manager())

    # wait until run_task_manager's TaskManager is in __aexit__
    await Timer(1)

    # cancel run_task_manager to see what happens when a TaskManager is cancelled when
    # waiting for finish in __aexit__
    task.cancel()
    await task.complete

    # ensure run_task_manager's children are also cancelled
    assert inner_task is not None
    assert inner_task.cancelled()
    assert outer_task is not None
    assert outer_task.cancelled()


@cocotb.test
@cocotb.parametrize(outer_continue_on_error=[True, False])
@cocotb.parametrize(inner_continue_on_error=[True, False])
async def test_external_cancel_in_nested_child_aexit(
    _: object, outer_continue_on_error: bool, inner_continue_on_error: bool
) -> None:
    outer_task: Task[Any] | None = None
    inner_task: Task[Any] | None = None

    async def run_task_manager() -> None:
        async with TaskManager(continue_on_error=outer_continue_on_error) as tm_outer:
            nonlocal outer_task
            outer_task = tm_outer.start_soon(coro(5, ret=9))

            @tm_outer.fork
            async def inner_block() -> None:
                async with TaskManager(
                    continue_on_error=inner_continue_on_error
                ) as tm_inner:
                    nonlocal inner_task
                    inner_task = tm_inner.start_soon(coro(5, ret=9))

    task = cocotb.start_soon(run_task_manager())

    # wait until run_task_manager's TaskManager is in __aexit__
    await Timer(1)

    # cancel run_task_manager to see what happens when a TaskManager is cancelled when
    # waiting for finish in __aexit__
    task.cancel()

    # ensure run_task_manager's children are cancelled, but outer_task will complete as CancelledError is ignored
    await task.complete
    # NullTrigger is necessary since cancellation will cause children to be cancelled,
    # but we can't wait for cancellation to complete, we must immediately propagate it.
    await NullTrigger()
    assert inner_task is not None
    assert inner_task.result() == 9
    assert outer_task is not None
    assert outer_task.cancelled()


@cocotb.test
@cocotb.parametrize(continue_on_error=[True, False])
async def test_external_cancel_in_block_ignored_at_end_of_block(
    _: object,
    continue_on_error: bool,
) -> None:
    async def run_task_manager() -> None:
        async with TaskManager(continue_on_error=continue_on_error):
            try:
                await Timer(2)
            except CancelledError:
                pass

    task = cocotb.start_soon(run_task_manager())

    # wait until run_task_manager's TaskManager is blocking
    await Timer(1)

    # cancel run_task_manager externally
    task.cancel()
    await task.complete
    assert not task.cancelled()
    assert task.exception() is not None


@cocotb.test
@cocotb.parametrize(continue_on_error=[True, False])
async def test_external_cancel_in_block_ignored_new_raise(
    _: object,
    continue_on_error: bool,
) -> None:
    async def run_task_manager() -> None:
        async with TaskManager(continue_on_error=continue_on_error):
            try:
                await Timer(2)
            except CancelledError:
                raise MyException()

    task = cocotb.start_soon(run_task_manager())

    # wait until run_task_manager's TaskManager is blocking
    await Timer(1)

    # cancel run_task_manager externally
    task.cancel()
    await task.complete
    assert not task.cancelled()
    assert task.exception() is not None


@cocotb.test
@cocotb.parametrize(continue_on_error=[True, False])
async def test_external_cancel_in_block_ignored_and_await(
    _: object,
    continue_on_error: bool,
) -> None:
    async def run_task_manager() -> None:
        async with TaskManager(continue_on_error=continue_on_error):
            try:
                await Timer(2)
            except CancelledError:
                pass

            await Timer(1)

    task = cocotb.start_soon(run_task_manager())

    # wait until run_task_manager's TaskManager is blocking
    await Timer(1)

    # cancel run_task_manager externally
    task.cancel()
    await task.complete
    assert not task.cancelled()
    assert task.exception() is not None


@cocotb.test
@cocotb.xfail(raises=RuntimeError, reason="Ignored CancelledError")
async def test_child_fails_ignore_cancel_at_end_of_block(_: object) -> None:
    async with TaskManager() as tm:
        tm.start_soon(raises_after(1))

        try:
            await Timer(2)
        except CancelledError:
            pass

    await Timer(1)


@cocotb.test
@cocotb.xfail(raises=RuntimeError, reason="Ignored CancelledError")
async def test_child_fails_ignore_cancel_and_await(_: object) -> None:
    async with TaskManager() as tm:
        tm.start_soon(raises_after(1))

        try:
            await Timer(2)
        except CancelledError:
            pass

        await Timer(1)


@cocotb.test
@cocotb.xfail(raises=RuntimeError, reason="Ignored CancelledError")
async def test_child_fails_ignore_cancel_new_raise(_: object) -> None:
    async with TaskManager() as tm:
        tm.start_soon(raises_after(1))

        try:
            await Timer(2)
        except CancelledError:
            raise MyException()


@cocotb.test
@cocotb.parametrize(continue_on_error=[True, False])
async def test_reused_context(_: object, continue_on_error: bool) -> None:
    tm = TaskManager(continue_on_error=continue_on_error)

    async with tm:
        tm.start_soon(coro(1))

    with pytest.raises(RuntimeError):
        async with tm:
            pass


@cocotb.test
async def test_start_soon_after_cancel_no_continue(_: object) -> None:
    try:
        async with TaskManager(continue_on_error=False) as tm:
            tm.start_soon(raises_after(1))

            try:
                await Timer(2)
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
async def test_start_soon_after_cancel_continue(_: object) -> None:
    try:
        async with TaskManager(continue_on_error=True) as tm:
            tm.start_soon(raises_after(1))
            await Timer(2)
            tm.start_soon(coro(2))

    except BaseExceptionGroup as e:
        my_exc, rest = e.split(MyException)
        assert my_exc is not None
        assert len(my_exc.exceptions) == 1
        assert rest is None


@cocotb.test
async def test_reraised_child_exception(_: object) -> None:
    try:
        async with TaskManager(continue_on_error=True) as tm:
            task = tm.start_soon(raises_after(1))
            # task will raise, but since continue_on_error=True, we will continue,
            # which will cause this await to re-raise the exception.
            await task

    except BaseExceptionGroup as e:
        my_exc, rest = e.split(MyException)
        assert my_exc is not None
        assert len(my_exc.exceptions) == 1
        assert rest is None


@cocotb.test
@cocotb.parametrize(continue_on_error=[True, False])
async def test_start_soon_outside_context(_: object, continue_on_error: bool) -> None:
    tm = TaskManager(continue_on_error=continue_on_error)
    with pytest.raises(RuntimeError):
        tm.start_soon(coro(1))


@cocotb.test
@cocotb.parametrize(continue_on_error=[True, False])
async def test_fork_outside_context(_: object, continue_on_error: bool) -> None:
    async def coro_noargs() -> None:
        await Timer(1)

    tm = TaskManager(continue_on_error=continue_on_error)
    with pytest.raises(RuntimeError):
        tm.fork(coro_noargs)


@cocotb.test
@cocotb.parametrize(continue_on_error=[True, False])
async def test_add_tasks_from_another_task(_: object, continue_on_error: bool) -> None:
    async def tm_coro(tm: TaskManager, ev: Event) -> int:
        async with tm:
            await ev.wait()
        return 10

    tm = TaskManager(continue_on_error=continue_on_error)
    ev = Event()
    tm_task = cocotb.start_soon(tm_coro(tm, ev))

    await NullTrigger()

    with pytest.raises(RuntimeError):
        tm.start_soon(coro(1))

    ev.set()

    await tm_task
    assert tm_task.result() == 10


@cocotb.test
@cocotb.parametrize(continue_on_error=[True, False])
async def test_start_soon_after_finished(_: object, continue_on_error: bool) -> None:
    async with TaskManager(continue_on_error=continue_on_error) as tm:
        tm.start_soon(coro(1))

    c = coro(1)
    with pytest.raises(RuntimeError):
        tm.start_soon(c)
    c.close()  # avoid ResourceWarning since we didn't await it.


@cocotb.test
@cocotb.parametrize(continue_on_error=[True, False])
async def test_cancel_child_task_in_block_and_exit(
    _: object, continue_on_error: bool
) -> None:
    cancelled = False

    async with TaskManager(continue_on_error=continue_on_error) as tm:

        @tm.fork
        async def child() -> None:
            try:
                await Timer(5)
            finally:
                nonlocal cancelled
                cancelled = True

        await Timer(1)
        child.cancel()

    assert cancelled


@cocotb.test
@cocotb.parametrize(continue_on_error=[True, False])
async def test_cancel_child_task_in_block_and_continue(
    _: object, continue_on_error: bool
) -> None:
    cancelled = False

    async with TaskManager(continue_on_error=continue_on_error) as tm:

        @tm.fork
        async def child() -> None:
            try:
                await Timer(5)
            finally:
                nonlocal cancelled
                cancelled = True

        await Timer(1)
        child.cancel()

        @tm.fork
        async def other() -> None:
            await Timer(1)

    assert cancelled
    assert other.done()


@cocotb.test
async def test_KeyboardInterrupt_in_block(_: object) -> None:
    with pytest.raises(KeyboardInterrupt):
        async with TaskManager() as tm:
            tm.start_soon(coro(5))

            await Timer(1)
            raise KeyboardInterrupt()


@cocotb.test
async def test_KeyboardInterrupt_in_nested_block(_: object) -> None:
    with pytest.raises(KeyboardInterrupt):
        async with TaskManager() as tm_outer:
            tm_outer.start_soon(coro(5))

            async with TaskManager() as tm_inner:
                tm_inner.start_soon(coro(5))

                await Timer(1)
                raise KeyboardInterrupt()


@cocotb.test
async def test_override_continue_on_error_continue(_: object) -> None:
    with assert_takes(2, "step"):
        try:
            async with TaskManager(continue_on_error=False) as tm:
                task1 = tm.start_soon(coro(2, ret=123))
                task2 = tm.start_soon(raises_after(1), continue_on_error=True)
        except BaseExceptionGroup as e:
            my_exc, rest = e.split(MyException)
            assert rest is None
            assert my_exc is not None
            assert len(my_exc.exceptions) == 1

    assert task1.result() == 123
    assert task2.exception() is not None


@cocotb.test
async def test_override_continue_on_error_fail(_: object) -> None:
    with assert_takes(1, "step"):
        try:
            async with TaskManager(continue_on_error=True) as tm:
                task1 = tm.start_soon(coro(2, ret=123))
                task2 = tm.start_soon(raises_after(1), continue_on_error=False)
        except BaseExceptionGroup as e:
            my_exc, rest = e.split(MyException)
            assert rest is None
            assert my_exc is not None
            assert len(my_exc.exceptions) == 1

    assert task1.cancelled()
    assert task2.exception() is not None


@cocotb.test
async def test_override_continue_on_error_fork_continue(_: object) -> None:
    with assert_takes(2, "step"):
        try:
            async with TaskManager(continue_on_error=False) as tm:
                task1 = tm.start_soon(coro(2, ret=123))

                @tm.fork(continue_on_error=True)
                async def task2() -> None:
                    await raises_after(1)
        except BaseExceptionGroup as e:
            my_exc, rest = e.split(MyException)
            assert rest is None
            assert my_exc is not None
            assert len(my_exc.exceptions) == 1

    assert task1.result() == 123
    assert task2.exception() is not None


@cocotb.test
async def test_override_continue_on_error_fork_fail(_: object) -> None:
    with assert_takes(1, "step"):
        try:
            async with TaskManager(continue_on_error=True) as tm:
                task1 = tm.start_soon(coro(2, ret=123))

                @tm.fork(continue_on_error=False)
                async def task2() -> None:
                    await raises_after(1)
        except BaseExceptionGroup as e:
            my_exc, rest = e.split(MyException)
            assert rest is None
            assert my_exc is not None
            assert len(my_exc.exceptions) == 1

    assert task1.cancelled()
    assert task2.exception() is not None


# Can't test KeyboardInterrupt in child Task since that will take a path to shut down
# the simulation.
