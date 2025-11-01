# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Handling JUnit XML."""

from __future__ import annotations

from typing import Any

from pytest import Config, StashKey, TestReport, hookimpl


class JUnitXML:
    def __init__(self, plugin: Any) -> None:
        """Create new instance of JUnit XML.

        Args:
            plugin: Handler to built-in pytest ``junitxml`` plugin.
        """
        self._plugin: Any = plugin  # NOTE: Type not available in public pytest API

    @staticmethod
    def register(config: Config) -> None:
        """Register new instance of JUnit XML if ``junitxml`` plugin was activated."""
        plugin: Any = config.pluginmanager.getplugin("junitxml")

        if plugin:
            # Instance of JUnit XML is stored in pytest stash where stash key to it
            # is stored in JUnix XML plugin
            key: StashKey | None = getattr(plugin, "xml_key", None)
            plugin = config.stash.get(key, None) if key else None

            if plugin:
                config.pluginmanager.register(JUnitXML(plugin))

    @hookimpl(tryfirst=True)
    def pytest_runtest_logreport(self, report: TestReport) -> None:
        """Fixing classname and name attributes when nodeid contains multiple [] (``runner[]::test[]``)."""
        # Pytest is using / as separator regardless of OS environment
        address = (
            report.nodeid.replace("/", ".").replace(".py::", ".").replace("::", ".")
        )
        classname, _, name = address.rpartition(".")
        reporter = self._plugin.node_reporter(report)

        reporter.add_attribute("classname", classname)
        reporter.add_attribute("name", name)
