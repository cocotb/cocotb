# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

# type: ignore  # distutils is untyped, so there's little reason to check this file

"""
Classes to compare simulation versions.

These are for cocotb-internal use only.

.. warning::
    These classes silently allow comparing versions of different simulators.
"""

from __future__ import annotations

import re
import subprocess
import sys

from cocotb_tools._vendor.distutils_version import LooseVersion

if sys.version_info >= (3, 11):
    from typing import Self


def _first_line(cmdline: str) -> str:
    output = cmdline.strip()
    if not output:
        raise ValueError("Unable to parse simulator version from empty output")
    return output.splitlines()[0]


def _first_version_token(cmdline: str) -> str:
    firstline = _first_line(cmdline)
    m = re.search(r"\d+(?:\.\d+[a-zA-Z]?)+(?:\.\d+)*", firstline)
    if not m:
        raise ValueError(f"Unable to parse simulator version from: {firstline}")
    return m.group(0)


def _run_version_command(command: tuple[str, ...]) -> str:
    result = subprocess.run(
        list(command),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return result.stdout


class SimulatorVersion(LooseVersion):
    """Base class for simulator-specific version constructors."""

    _sim_command: tuple[str, ...] | None = None

    def _cmp(self, other):
        if isinstance(other, str):
            other = self.__class__(other)
        elif not isinstance(other, LooseVersion):
            return NotImplemented

        if self.version == other.version:
            return 0
        if self.version < other.version:
            return -1
        if self.version > other.version:
            return 1

    @classmethod
    def from_commandline(cls, cmdline: str | None = None) -> Self:
        """Construct from simulator command-line version output.

        If *cmdline* is omitted, the simulator version command is executed.
        """
        if cmdline is None:
            if cls._sim_command is None:
                raise ValueError(f"{cls.__name__} does not define a version command")
            cmdline = _run_version_command(cls._sim_command)
        return cls(cls._extract_version_from_commandline(cmdline))

    @classmethod
    def _extract_version_from_commandline(cls, cmdline: str) -> str:
        return _first_line(cmdline)

    @classmethod
    def from_sim_version(cls, sim_version: str | None = None) -> Self:
        """Construct from ``cocotb.SIM_VERSION``.

        If *sim_version* is omitted, ``cocotb.SIM_VERSION`` is read from the
        active simulation.
        """
        if sim_version is None:
            import cocotb  # noqa: PLC0415

            sim_version = cocotb.SIM_VERSION
        return cls(sim_version)


class ActivehdlVersion(SimulatorVersion):
    """Version numbering class for Aldec Active-HDL.

    Example:
        >>> ActivehdlVersion("10.5a.12.6914") > ActivehdlVersion("10.5.216.6767")
        True
    """

    _sim_command = ("vsimsa", "-version")

    def parse(self, vstring):
        self.vstring = vstring
        version = []

        for part in vstring.split("."):
            match = re.fullmatch(r"(\d+)([a-zA-Z]?)", part)
            if match is None:
                super().parse(vstring)
                return

            version.append(int(match.group(1)))

            suffix = match.group(2)
            if suffix:
                version.append(ord(suffix.lower()) - ord("a") + 1)
            else:
                version.append(0)

        self.version = version

    @classmethod
    def _extract_version_from_commandline(cls, cmdline: str) -> str:
        return _first_version_token(cmdline)


class CvcVersion(SimulatorVersion):
    """Version numbering class for Tachyon DA CVC.

    Example:
        >>> CvcVersion(
        ...     "OSS_CVC_7.00b-x86_64-rhel6x of 07/07/14 (Linux-elf)"
        ... ) > CvcVersion("OSS_CVC_7.00a-x86_64-rhel6x of 07/07/14 (Linux-elf)")
        True
    """

    _sim_command = ("cvc64", "-version")


class GhdlVersion(SimulatorVersion):
    """Version numbering class for GHDL."""

    _sim_command = ("ghdl", "--version")

    def parse(self, vstring):
        self.vstring = vstring
        m = re.match(r"(\d+(?:\.\d+)*)(?:[- ](dev|devel)\b.*|.*)", vstring)
        if not m:
            super().parse(vstring)
            return

        version = [int(component) for component in m.group(1).split(".")]
        while len(version) < 3:
            version.append(0)
        version.append(-1 if m.group(2) else 0)
        self.version = version

    @classmethod
    def _extract_version_from_commandline(cls, cmdline: str) -> str:
        firstline = _first_line(cmdline)
        m = re.match(r"^GHDL\s+(\S+)", firstline, re.IGNORECASE)
        if not m:
            raise ValueError(f"Unable to parse GHDL version from: {firstline}")
        return m.group(1)


class IcarusVersion(SimulatorVersion):
    """Version numbering class for Icarus Verilog.

    Example:
        >>> IcarusVersion("11.0 (devel)") > IcarusVersion("10.3 (stable)")
        True
        >>> IcarusVersion("10.3 (stable)") <= IcarusVersion("10.3 (stable)")
        True
    """

    _sim_command = ("iverilog", "-V")

    @classmethod
    def _extract_version_from_commandline(cls, cmdline: str) -> str:
        firstline = _first_line(cmdline)
        m = re.match(r"^Icarus Verilog version (\d+\.\d+)", firstline)
        if not m:
            raise ValueError(
                f"Unable to parse Icarus Verilog version from: {firstline}"
            )
        return m.group(1)


class ModelsimVersion(SimulatorVersion):
    """Version numbering class for Mentor ModelSim."""

    _sim_command = ("vsim", "-version")

    @classmethod
    def _extract_version_from_commandline(cls, cmdline: str) -> str:
        firstline = _first_line(cmdline)
        m = re.search(r"\bvsim\s+(\S+)", firstline, re.IGNORECASE)
        if not m:
            raise ValueError(f"Unable to parse ModelSim version from: {firstline}")
        return m.group(1)


class QuestaVersion(SimulatorVersion):
    """Version numbering class for Mentor Questa.

    Example:
        >>> QuestaVersion("10.7c 2018.08") > QuestaVersion("10.7b 2018.06")
        True
        >>> QuestaVersion("2020.1 2020.01") > QuestaVersion("10.7c 2018.08")
        True
        >>> QuestaVersion("2020.1 2020.01") == QuestaVersion("2020.1")
        True
        >>> QuestaVersion("2023.1_2 2023.03") > QuestaVersion("2023.1_1")
        True
    """

    _sim_command = ("vsim", "-version")

    def parse(self, vstring):
        # A Questa version string, as returned by the simulator, consists of two
        # space-separated parts. The first part is the actual version number,
        # the second part seems to be the year and month of the initial release.
        # We only need the first part, which is also used in public
        # communication by Siemens.
        try:
            first_component = vstring.split(" ", 1)[0]
        except IndexError:
            first_component = vstring

        super().parse(first_component)

    @classmethod
    def _extract_version_from_commandline(cls, cmdline: str) -> str:
        firstline = _first_line(cmdline)
        m = re.search(r"\bvsim\s+(\S+)", firstline, re.IGNORECASE)
        if not m:
            raise ValueError(f"Unable to parse Questa version from: {firstline}")
        return m.group(1)


class RivieraVersion(SimulatorVersion):
    """Version numbering class for Aldec Riviera-PRO.

    Example:
        >>> RivieraVersion("2019.10.138.7537") == RivieraVersion("2019.10.138.7537")
        True
    """

    _sim_command = ("vsimsa", "-version")

    @classmethod
    def _extract_version_from_commandline(cls, cmdline: str) -> str:
        return _first_version_token(cmdline)


class VcsVersion(SimulatorVersion):
    """Version numbering class for Synopsys VCS.

    Example:
        >>> VcsVersion("Q-2020.03-1_Full64") > VcsVersion("K-2015.09_Full64")
        True
    """

    _sim_command = ("vcs", "-full64", "-version")

    def parse(self, vstring):
        self.vstring = vstring
        m = re.search(r"(\d{4})\.(\d{2})(?:-(\d+))?", vstring)
        if not m:
            super().parse(vstring)
            return

        year, month, patch = m.groups()
        self.version = [int(year), int(month), int(patch or 0)]

    @classmethod
    def _extract_version_from_commandline(cls, cmdline: str) -> str:
        firstline = _first_line(cmdline)
        m = re.search(r"(?:[A-Z]-)?\d{4}\.\d{2}(?:-\d+)?(?:_Full\d+)?", firstline)
        if not m:
            raise ValueError(f"Unable to parse VCS version from: {firstline}")
        return m.group(0)


class VerilatorVersion(SimulatorVersion):
    """Version numbering class for Verilator.

    Example:
        >>> VerilatorVersion("4.032 2020-04-04") > VerilatorVersion("4.031 devel")
        True
    """

    _sim_command = ("verilator", "--version")

    @classmethod
    def _extract_version_from_commandline(cls, cmdline: str) -> str:
        """Parse the output of ``verilator --version``.

        Example:
            >>> cmdline = "Verilator 5.041 devel rev v5.040-1-g4eb030717"
            >>> VerilatorVersion.from_commandline(cmdline) >= VerilatorVersion("5.040")
            True

        Args:
            cmdline: The command-line output of a call to ``verilator --version``.

        Returns:
            An instance of :class:`VerilatorVersion`.

        Raises:
            AssertionError: If *cmdline* does not appear to be generated by Verilator.
        """
        firstline = _first_line(cmdline)
        sim, version, *version_extra = firstline.strip().split(" ")
        assert sim == "Verilator"
        return version


class XceliumVersion(SimulatorVersion):
    """Version numbering class for Cadence Xcelium.

    Example:
        >>> XceliumVersion("20.06-g183") > XceliumVersion("20.03-s002")
        True
        >>> XceliumVersion("20.07-e501") > XceliumVersion("20.06-g183")
        True
    """

    _sim_command = ("xrun", "--version")

    @classmethod
    def _extract_version_from_commandline(cls, cmdline: str) -> str:
        firstline = _first_line(cmdline)
        m = re.search(
            r"(?:xrun[^:]*:\s*)?(\d+\.\d+-[a-z]\d+)",
            firstline,
            re.IGNORECASE,
        )
        if not m:
            raise ValueError(f"Unable to parse Xcelium version from: {firstline}")
        return m.group(1)


class IusVersion(XceliumVersion):  # inherit everything from Xcelium
    """Version numbering class for Cadence IUS.

    Example:
        >>> IusVersion("15.20-s050") > IusVersion("15.20-s049")
        True
    """

    _sim_command = ("irun", "-version")


class NvcVersion(SimulatorVersion):
    """Version numbering class for NVC."""

    _sim_command = ("nvc", "--version")

    @classmethod
    def _extract_version_from_commandline(cls, cmdline: str) -> str:
        firstline = _first_line(cmdline)
        sim, version, *version_extra = firstline.strip().split(" ")
        assert sim == "nvc"
        return version
