# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Cocotb plugin to run on top of cocotb simulator runners."""

import inspect
import os
from collections.abc import Generator, Iterable

from pytest import (
    Class,
    Collector,
    CollectReport,
    Config,
    Function,
    Item,
    Module,
    Session,
    StashKey,
    TestReport,
    hookimpl,
)

import cocotb
from cocotb_tools.pytest.reporter import Reporter
from cocotb_tools.pytest.runner import Runner


class Handler:
    def __getitem__(self, key: str) -> "Handler":
        return Handler()

    def __getattr__(self, key: str) -> "Handler":
        return Handler()

    def __len__(self) -> int:
        return 0


class Controller:
    def __init__(self, config: Config):
        self._reporter: Reporter = Reporter()
        self._config: Config = config
        self._keywords: dict[str, set[str]] = {}
        self._junitxml = None

        junitxml = config.pluginmanager.getplugin("junitxml")

        if junitxml:
            key: StashKey | None = getattr(junitxml, "xml_key", None)
            self._junitxml = config.stash.get(key, None) if key else None

    @hookimpl(tryfirst=True)
    def pytest_configure(config: Config) -> None:
        setattr(cocotb, "SIM_NAME", "")
        setattr(cocotb, "SIM_VERSION", "")
        setattr(cocotb, "top", Handler())

    @hookimpl(tryfirst=True, wrapper=True)
    def pytest_pycollect_makeitem(
        self, collector: Module | Class, name: str, obj: object
    ) -> Generator[None | Item | Collector | list[Item | Collector], None, None]:
        result: None | Item | Collector | list[Item | Collector] = yield

        if result is None:
            return None

        items: Iterable[Item | Collector] = (
            result if isinstance(result, list) else (result,)
        )

        return list(self._collect(collector, items))

    @hookimpl(tryfirst=True)
    def pytest_runtest_setup(self, item: Item) -> None:
        os.environ["COCOTB_PYTEST_NODEID"] = item.nodeid
        os.environ["COCOTB_PYTEST_KEYWORDS"] = ",".join(item.keywords)

    @hookimpl(trylast=True)
    def pytest_runtest_logfinish(
        self, nodeid: str, location: tuple[str, int | None, str]
    ) -> None:
        config: Config = self._config
        hook = config.hook

        for data in self._reporter:
            report: CollectReport | TestReport | None = (
                hook.pytest_report_from_serializable(config=config, data=data)
            )

            if isinstance(report, TestReport):
                if self._junitxml:
                    address = report.nodeid.replace("/", ".").replace(".py::", ".")
                    classname, _, name = address.rpartition(".")
                    reporter = self._junitxml.node_reporter(report)

                    reporter.add_attribute("classname", classname)
                    reporter.add_attribute("name", name)

                hook.pytest_runtest_logreport(report=report)

    @hookimpl(tryfirst=True, wrapper=True)
    def pytest_runtestloop(self, session: Session) -> Generator[None, None, None]:
        with self._reporter:
            yield

    def _collect(
        self, collector: Collector, items: Iterable[Item | Collector]
    ) -> Generator[Item | Collector, None, None]:
        collectonly: bool = collector.config.option.collectonly
        runner: Runner | None = collector.getparent(Runner)

        for item in items:
            if isinstance(item, Function) and item.get_closest_marker("cocotb"):
                if inspect.iscoroutinefunction(item.function):
                    if runner:
                        self._add_keywords(item.nodeid, runner.item.keywords)
                        runner.item.extra_keyword_matches.update(item.keywords)
                    elif collectonly:
                        yield item
                elif not runner:
                    modules: Iterable[str] | None = None

                    for marker in item.iter_markers("cocotb"):
                        if marker.args:
                            modules = marker.args
                            break

                    yield item

                    if item.parent:
                        yield Runner.from_parent(
                            item.parent,
                            name=item.name,
                            item=item,
                            modules=modules,
                        )
            else:
                yield item

    @hookimpl(tryfirst=True)
    def pytest_collection_modifyitems(
        self, session: Session, config: Config, items: list[Item]
    ) -> None:
        if config.option.collectonly:
            for item in items:
                keywords: set[str] | None = self._keywords.get(item.nodeid)

                if keywords:
                    item.extra_keyword_matches.update(keywords)

    def _add_keywords(self, nodeid: str, keywords: Iterable[str]):
        entries: set[str] | None = self._keywords.get(nodeid)

        if entries is None:
            self._keywords[nodeid] = set(keywords)
        else:
            entries.update(keywords)
