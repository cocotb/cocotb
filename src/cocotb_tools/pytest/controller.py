# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Cocotb plugin to run on top of cocotb simulator runners."""

from __future__ import annotations

import inspect
import os
from collections.abc import Generator, Iterable, Sequence
from pathlib import PurePosixPath

from pytest import (
    Class,
    Collector,
    CollectReport,
    Config,
    Function,
    Item,
    MarkDecorator,
    Module,
    Session,
    StashKey,
    TestReport,
    hookimpl,
    mark,
)

import cocotb
from cocotb_tools.pytest.reporter import Reporter
from cocotb_tools.pytest.runner import Runner


class Handler:
    def __getitem__(self, key: str) -> Handler:
        return Handler()

    def __getattr__(self, key: str) -> Handler:
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
    ) -> Generator[Item | Collector | list[Item | Collector] | None, None, None]:
        result: Item | Collector | list[Item | Collector] | None = yield

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
                report.nodeid = self._get_mangled_nodeid(report)

                if self._junitxml:
                    self._attach_properties_to_junit_xml(report)

                hook.pytest_runtest_logreport(report=report)

    @staticmethod
    def _split_nodeid(nodeid: str) -> tuple[PurePosixPath, str]:
        """Split provided node identifier to path and function name.

        Args:
            nodeid: Item nodeid in form of ``<path_to_file>::[<class_name>::]<function_name>``.

        Returns:
            Two-elements tuple with path to file and name of function with scope.
        """
        (path, _, function) = nodeid.partition("::")

        return PurePosixPath(path), function

    def _get_mangled_nodeid(self, report: TestReport) -> str:
        """Get mangled address of test node identifier as combination of node identifiers from cocotb runner and test.

        Pytest is always using ``/`` as path separator (compatible with POSIX).
        Node identifier is mostly represented as: ``<path_to_file>::[<class_name>::]<function_name>``

        To get unique test identifier for cocotb test from various different cocotb runners,
        we need to combine node identifier from cocotb runner and cocotb test.

        Args:
            report: Test report from simulator (pytest sub-process).

        Returns:
            Mangled node identifer.
        """
        runner_nodeid: str = getattr(report, "runner_nodeid", "")
        runner_path, runner_function = self._split_nodeid(runner_nodeid)
        item_path, item_function = self._split_nodeid(report.nodeid)

        if runner_path.parts == item_path.parts:
            return f"{runner_nodeid}::{item_function}"

        try:
            relative: PurePosixPath = item_path.relative_to(runner_path.parent)
            parts: tuple[str, ...] = relative.parent.parts
            packages: str = ".".join(parts) + "." if parts else ""

            return f"{runner_nodeid}::{packages}{relative.stem}::{item_function}"
        except ValueError:
            return f"{runner_nodeid}::{report.nodeid}"

    def _attach_properties_to_junit_xml(self, report: TestReport) -> None:
        address = report.nodeid.replace("/", ".").replace(".py::", ".")
        classname, _, name = address.rpartition("::")
        reporter = self._junitxml.node_reporter(report)

        reporter.add_attribute("classname", classname)
        reporter.add_attribute("name", name)

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
                    test_module: Sequence[str] | str = ""

                    for marker in item.iter_markers("cocotb"):
                        test_module = marker.kwargs.get("test_module", marker.args)

                        if test_module:
                            break

                    if not test_module:
                        test_module = item.path.name.partition(".")[0]

                    hdl_toplevel: str = (
                        test_module if isinstance(test_module, str) else test_module[0]
                    )

                    if hdl_toplevel.startswith("test_"):
                        hdl_toplevel = hdl_toplevel.removeprefix("test_")
                    elif hdl_toplevel.endswith("_test"):
                        hdl_toplevel = hdl_toplevel.removesuffix("_test")

                    marker: MarkDecorator = mark.cocotb(
                        test_module=test_module,
                        hdl_toplevel=hdl_toplevel,
                        # TODO: test_dir=os.path.join(build_dir, test_dir),
                    )

                    item.add_marker(marker)

                    yield item

                    if item.parent:
                        yield Runner.from_parent(
                            item.parent,
                            name=item.name,
                            item=item,
                            test_module=test_module,
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
