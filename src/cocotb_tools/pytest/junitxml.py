# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Handling JUnit XML."""

from __future__ import annotations

from _pytest.junitxml import LogXML, xml_key
from pytest import Config, TestReport, hookimpl


class JUnitXML:
    def __init__(self, log_xml: LogXML) -> None:
        """Create new instance of JUnit XML.

        Args:
            plugin: Handler to built-in pytest ``junitxml`` plugin.
        """
        self._log_xml: LogXML = log_xml

    @staticmethod
    def register(config: Config) -> None:
        """Register new instance of JUnit XML if ``junitxml`` plugin was activated."""
        log_xml: LogXML | None = config.stash.get(xml_key, None)

        if log_xml:
            config.pluginmanager.register(JUnitXML(log_xml))

    @hookimpl(tryfirst=True)
    def pytest_runtest_logreport(self, report: TestReport) -> None:
        """Fixing classname and name attributes when nodeid contains multiple [] (``runner[]::test[]``)."""
        # Pytest is using / as separator regardless of OS environment
        address = (
            report.nodeid.replace("/", ".").replace(".py::", ".").replace("::", ".")
        )
        classname, _, name = address.rpartition(".")
        reporter = self._log_xml.node_reporter(report)

        reporter.add_attribute("classname", classname)
        reporter.add_attribute("name", name)
