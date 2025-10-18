# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Pytest regression manager for cocotb."""

from __future__ import annotations

import hashlib
import inspect
import random
import sys
from collections import deque
from collections.abc import AsyncGenerator, Generator, Iterable
from functools import wraps
from multiprocessing.connection import Client
from typing import Any, Callable, Literal

from _pytest.config import default_plugins
from pytest import (
    CallInfo,
    Class,
    Collector,
    Config,
    ExitCode,
    FixtureDef,
    Function,
    Item,
    Module,
    PytestPluginManager,
    Session,
    TestReport,
    hookimpl,
    mark,
)

import cocotb
from cocotb import simulator
from cocotb._extended_awaitables import with_timeout
from cocotb._gpi_triggers import Timer
from cocotb.simtime import TimeUnit, get_sim_time
from cocotb.task import Task
from cocotb_tools.pytest import env
from cocotb_tools.pytest.fixture import (
    AsyncFixture,
    AsyncFixtureCachedResult,
    resolve_fixture_arg,
)


def finish_on_exception(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs) -> Any:
        try:
            return method(self, *args, **kwargs)
        except BaseException as e:
            self._finish()
            raise e

    return wrapper


def per_stage(item: Item) -> int:
    for marker in item.iter_markers("cocotb"):
        if "stage" in marker.kwargs:
            return marker.kwargs["stage"]

    return 0


class RegressionManager:
    """Pytest regression manager for cocotb."""

    _timer1 = Timer(1)

    def __init__(self, *args, **kwargs):
        self._task: Task
        self._tasks: deque[Task] = deque[Task]()
        self._subtasks: list[Task] = []
        self._scheduled: bool = False
        self._index: int = 0
        self._finished: bool = False
        self._call_start: float | None = None
        self._sim_time_start: float = 0
        self._nodeid: str = env.as_str("COCOTB_PYTEST_NODEID") + "::"
        self._keywords: list[str] = env.as_list("COCOTB_PYTEST_KEYWORDS")

        pluginmanager = PytestPluginManager()

        # Initialize configuration object needed for pytest
        config: Config = Config(
            pluginmanager,
            invocation_params=Config.InvocationParams(
                args=args,
                plugins=None,
                dir=env.as_path("COCOTB_PYTEST_DIR"),
            ),
        )

        if args:
            # Handle any "-p no:plugin" args.
            pluginmanager.consider_preparse(args, exclude_only=True)

        for plugin in default_plugins:
            pluginmanager.import_plugin(plugin)

        # Register itself as plugin
        config.pluginmanager.register(self, name="cocotb_regression_manager")

        # Parse pytest command line arguments, including from PYTEST_ADDOPTS environment variable
        config = config.pluginmanager.hook.pytest_cmdline_parse(
            pluginmanager=config.pluginmanager, args=list(args)
        )

        if env.exists("COCOTB_TEST_MODULES"):
            config.args = env.as_list("COCOTB_TEST_MODULES")

        # Create session context for tests
        self._session: Session = Session.from_config(config)
        self._session.exitstatus = ExitCode.OK  # this is unset in pytest by default

        # Call all pytest_configure hooks from registered plugins to configure config object
        self._session.config._do_configure()

    @finish_on_exception
    def start_regression(self) -> None:
        """Start regression manager."""
        self._session.config.hook.pytest_sessionstart(session=self._session)
        self._session.config.hook.pytest_collection(session=self._session)
        self._session.config.hook.pytest_runtestloop(session=self._session)

    @hookimpl(tryfirst=True, wrapper=True)
    def pytest_pycollect_makeitem(
        self, collector: Module | Class, name: str, obj: object
    ) -> Generator[Item | Collector | list[Item | Collector] | None, None, None]:
        result: Item | Collector | list[Item | Collector] | None = yield

        if result is None:
            return None

        items: Iterable[Item | Collector] = (
            result if isinstance(result, list) else (result,)
        )

        return list(self._collect(items))

    @hookimpl(tryfirst=True)
    def pytest_runtestloop(self, session: Session) -> bool:
        if (
            session.testsfailed
            and not session.config.option.continue_on_collection_errors
        ):
            raise session.Interrupted(
                f"{session.testsfailed} error{'s' if session.testsfailed != 1 else ''} during collection"
            )

        if not session.config.option.collectonly and session.items:
            item, nextitem = self._get_item()
            item.config.hook.pytest_runtest_protocol(item=item, nextitem=nextitem)
        else:
            self._finish()

        return True

    @hookimpl(tryfirst=True)
    def pytest_runtest_protocol(self, item: Item, nextitem: Item | None) -> bool:
        item.ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
        self._setup()

        return True

    @property
    def _item(self) -> Item:
        """Get current pytest item (test)."""
        return self._session.items[self._index]

    @property
    def _nextitem(self) -> Item | None:
        """Get next pytest item (test) needed by test teardown phase."""
        index: int = self._index + 1

        return self._session.items[index] if index < len(self._session.items) else None

    def _collect(
        self, items: Iterable[Item | Collector]
    ) -> Generator[Item | Collector, None, None]:
        for item in items:
            if not isinstance(item, Function):
                yield item

            elif "cocotb" in item.keywords and inspect.iscoroutinefunction(
                item.function
            ):
                if not item.nodeid.startswith(self._nodeid):
                    setattr(item, "_nodeid", self._nodeid + item.nodeid)

                kwargs: dict[str, Any] = {}

                for marker in reversed(list(item.iter_markers("cocotb"))):
                    kwargs.update(marker.kwargs)

                if kwargs.get("skip"):
                    item.add_marker("skip")

                if kwargs.get("expect_fail"):
                    raises: BaseException | tuple[BaseException] | None = kwargs.get(
                        "expect_error"
                    )
                    item.add_marker(
                        mark.xfail(raises=raises if raises else None, strict=True)
                    )

                timeout: float | int = kwargs.get("timeout_time", 0)

                if timeout:
                    unit: TimeUnit = kwargs.get("timeout_unit", "step")
                    f = item.obj

                    @wraps(f)
                    async def func(*args: object, **kwargs: object) -> None:
                        await with_timeout(f(*args, **kwargs), timeout, unit)

                    item.obj = func

                item.extra_keyword_matches.update(self._keywords)

                yield item

    def _call_and_report(
        self,
        item: Item,
        when: Literal["setup", "call", "teardown"],
        func: Callable[..., None] | None = None,
        **kwargs,
    ) -> bool:
        if not func:
            func = getattr(item.ihook, f"pytest_runtest_{when}")
            kwargs["item"] = item
            self._call_start = None

        reraise: tuple[type[BaseException], ...] = ()

        if not item.config.getoption("usepdb", False):
            reraise += (KeyboardInterrupt,)

        call: CallInfo = CallInfo.from_call(
            lambda: func(**kwargs),
            when=when,
            reraise=reraise,
        )

        sim_time_unit: TimeUnit = self._session.config.option.cocotb_sim_time_unit

        if self._call_start is None:
            self._call_start = call.start
            self._sim_time_start = get_sim_time(sim_time_unit)
        else:
            call.start = self._call_start
            call.duration = call.stop - call.start

        if call.excinfo or not self._tasks:
            sim_time_start: float = self._sim_time_start
            sim_time_stop: float = get_sim_time(sim_time_unit)
            sim_time_duration: float = sim_time_stop - sim_time_start

            report: TestReport = item.ihook.pytest_runtest_makereport(
                item=item, call=call
            )

            properties: dict[str, Any] = {
                "cocotb": True,
                "sim_time_start": sim_time_start,
                "sim_time_stop": sim_time_stop,
                "sim_time_duration": sim_time_duration,
                "sim_time_unit": sim_time_unit,
                "random_seed": cocotb.RANDOM_SEED,
            }

            report.__dict__.update(properties)
            report.user_properties.extend(properties.items())

            item.ihook.pytest_runtest_logreport(report=report)

            return report.passed

        return False

    @finish_on_exception
    def _setup(self, task: Task | None = None) -> None:
        item: Item = self._item
        func = task.result if task else None
        passed: bool = self._call_and_report(item, "setup", func=func)

        if self._tasks:
            self._execute(self._setup, self._tasks.popleft())
        elif passed:
            self._call()
        else:
            self._teardown()

    @finish_on_exception
    def _call(self, task: Task | None = None) -> None:
        item: Item = self._item
        func = task.result if task else None
        self._call_and_report(item, "call", func=func)

        if self._tasks:
            self._execute(self._call, self._tasks.popleft())
        else:
            self._teardown()

    @finish_on_exception
    def _teardown(self, task: Task | None = None) -> None:
        item: Item = self._item
        nextitem: Item | None = self._nextitem

        if task:
            self._call_and_report(item, "teardown", func=task.result)
        else:
            self._call_and_report(item, "teardown", nextitem=nextitem)

        if self._tasks:
            return self._execute(self._teardown, self._tasks.popleft())

        item.ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)

        if nextitem:
            item, nextitem = self._pop_item()
            item.config.hook.pytest_runtest_protocol(item=item, nextitem=nextitem)
        else:
            self._finish()

    def _get_item(self) -> tuple[Item, Item | None]:
        return self._item, self._nextitem

    def _pop_item(self) -> tuple[Item, Item | None]:
        self._index += 1

        return self._get_item()

    def _finish(self) -> None:
        if self._finished:  # this method must be called once
            return

        self._finished = True

        self._session.config.hook.pytest_sessionfinish(
            session=self._session,
            exitstatus=self._session.exitstatus,
        )

        self._session.config._ensure_unconfigure()
        self._shutdown()

    @hookimpl(tryfirst=True)
    def pytest_collection_modifyitems(
        self, session: Session, config: Config, items: list[Item]
    ) -> None:
        items[:] = sorted(items, key=per_stage)

    @hookimpl(tryfirst=True)
    def pytest_runtest_setup(self, item: Item) -> None:
        # seed random number generator based on test module, name, and COCOTB_RANDOM_SEED
        hasher = hashlib.sha1()
        hasher.update(item.nodeid.encode())
        seed = cocotb.RANDOM_SEED + int(hasher.hexdigest(), 16)
        random.seed(seed)

    @hookimpl(tryfirst=True)
    def pytest_fixture_setup(
        self,
        fixturedef: FixtureDef[Any],
        request,
    ) -> object | None:
        """Execution of fixture setup."""
        fixturefunc = fixturedef.func
        is_coroutine: bool = inspect.iscoroutinefunction(fixturefunc)
        is_async_generator: bool = inspect.isasyncgenfunction(fixturefunc)

        if not is_coroutine and not is_async_generator:
            return None

        async def func() -> Any:
            self._subtasks = []

            kwargs: dict[str, Any] = {
                argname: resolve_fixture_arg(request.getfixturevalue(argname))
                for argname in fixturedef.argnames
            }

            try:
                if is_async_generator:
                    iterator: AsyncGenerator[Any, None] = fixturefunc(**kwargs)
                    result = await iterator.__anext__()
                    fixturedef.addfinalizer(self._create_async_finalizer(iterator))
                else:
                    result = await fixturefunc(**kwargs)

                return result
            finally:
                fixturedef.addfinalizer(self._create_tasks_finalizer())

        task: Task = AsyncFixture(func())

        cache_key = fixturedef.cache_key(request)
        fixturedef.cached_result = AsyncFixtureCachedResult((task, cache_key, None))

        self._tasks.append(task)

        return True

    @hookimpl(tryfirst=True)
    def pytest_pyfunc_call(self, pyfuncitem: Function) -> object | None:
        testfunction = pyfuncitem.obj

        if not inspect.iscoroutinefunction(testfunction):
            return None

        async def func() -> None:
            funcargs = pyfuncitem.funcargs
            self._subtasks = []

            kwargs: dict[str, Any] = {
                argname: resolve_fixture_arg(funcargs[argname])
                for argname in pyfuncitem._fixtureinfo.argnames
            }

            try:
                await testfunction(**kwargs)
            finally:
                pyfuncitem.addfinalizer(self._create_tasks_finalizer())

        self._tasks.clear()
        self._tasks.append(Task(func()))

        return True

    @hookimpl(tryfirst=True)
    def pytest_runtest_logreport(self, report: TestReport) -> None:
        address: str = env.as_str("COCOTB_PYTEST_REPORTER_ADDRESS")

        if address:
            config: Config = self._session.config

            with Client(address) as client:
                data: dict[str, Any] = config.hook.pytest_report_to_serializable(
                    config=config, report=report
                )
                client.send(data)

    def _create_async_finalizer(
        self, iterator: AsyncGenerator[Any, None]
    ) -> Callable[[], object]:
        def finalizer() -> None:
            async def func() -> None:
                try:
                    await iterator.__anext__()
                except StopAsyncIteration:
                    pass

            self._tasks.append(Task(func()))

        return finalizer

    def _create_tasks_finalizer(self) -> Callable[[], object]:
        def finalizer() -> None:
            tasks: list[Task] = self._subtasks

            for task in reversed(tasks):
                task._cancel_now()

        self._subtasks = []

        return finalizer

    @property
    def _running_test(self) -> RegressionManager:
        return self

    def add_task(self, task: Task) -> None:
        self._subtasks.append(task)

    def _fail_simulation(self, msg: str) -> None:
        sys.stderr.write(msg + "\n")
        sys.stderr.flush()
        self._session.exitstatus = ExitCode.INTERNAL_ERROR
        self._finish()

    def _execute(self, done_callback: Callable[..., None], task: Task) -> None:
        task._add_done_callback(done_callback)
        self._task = task

        if self._scheduled:
            self._timer1._register(self._schedule_next_task)
        else:
            self._scheduled = True
            self._schedule_next_task()

    def _schedule_next_task(self) -> None:
        self._task._ensure_started()
        cocotb._event_loop._inst.run()

    def _shutdown(self) -> None:
        # TODO refactor initialization and finalization into their own module
        # to prevent circular imports requiring local imports
        from cocotb._init import _shutdown_testbench  # noqa: PLC0415

        _shutdown_testbench()

        # Setup simulator finalization
        simulator.stop_simulator()
