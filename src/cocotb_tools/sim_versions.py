# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Classes to compare simulation versions.

These are for cocotb-internal use only.

.. warning::
    These classes silently allow comparing versions of different simulators.
"""

from __future__ import annotations

import re
import subprocess
from functools import total_ordering
from typing import ClassVar, Optional


def _letter_value(letter: str) -> int:
    if not letter:
        return -1
    return ord(letter.lower()) - ord("a")


def _normalize_release_numbers(numbers: tuple[int, ...]) -> tuple[int, ...]:
    result = list(numbers)
    while result and result[-1] == 0:
        result.pop()
    return tuple(result)


@total_ordering
class SimulatorVersion:
    """Base class for simulator version comparison."""

    command: ClassVar[tuple[str, ...] | None] = None

    def __init__(self, vstring: str) -> None:
        self.vstring = vstring.strip()
        self._parsed = self._parse(self.vstring)
        # Preserve the LooseVersion-compatible attribute name.
        self.version = self._parsed

    def __repr__(self) -> str:
        return f'{type(self).__name__}("{self.vstring}")'

    def __str__(self) -> str:
        return self.vstring

    def _coerce_other(self, other: object) -> SimulatorVersion:
        if isinstance(other, str):
            return type(self)(other)
        if isinstance(other, SimulatorVersion):
            return type(self)(str(other))
        return NotImplemented

    def __eq__(self, other: object) -> bool:
        other_version = self._coerce_other(other)
        if other_version is NotImplemented:
            return NotImplemented
        return self._parsed == other_version._parsed

    def __lt__(self, other: object) -> bool:
        other_version = self._coerce_other(other)
        if other_version is NotImplemented:
            return NotImplemented
        return self._parsed < other_version._parsed

    @classmethod
    def from_sim_version(cls, sim_version: Optional[str] = None) -> SimulatorVersion:
        if sim_version is None:
            import cocotb

            sim_version = cocotb.SIM_VERSION
        return cls(sim_version)

    @classmethod
    def from_commandline(cls, cmdline: Optional[str] = None) -> SimulatorVersion:
        if cmdline is None:
            cmdline = cls._run_version_command()
        return cls(cls._extract_version_from_commandline(cmdline))

    @classmethod
    def _run_version_command(cls) -> str:
        if cls.command is None:
            raise NotImplementedError(f"{cls.__name__} does not define a version command")
        result = subprocess.run(
            list(cls.command),
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        return result.stdout

    @classmethod
    def _extract_version_from_commandline(cls, cmdline: str) -> str:
        return cmdline.strip().splitlines()[0]

    @classmethod
    def _parse(cls, vstring: str) -> tuple[object, ...]:
        raise NotImplementedError


class _SimpleDottedVersion(SimulatorVersion):
    _pattern: ClassVar[re.Pattern[str]] = re.compile(r"(\d+(?:\.\d+)*)")

    @classmethod
    def _parse(cls, vstring: str) -> tuple[object, ...]:
        match = cls._pattern.search(vstring)
        if not match:
            raise ValueError(f"Unable to parse {cls.__name__} from: {vstring}")
        numbers = tuple(int(part) for part in match.group(1).split("."))
        return (_normalize_release_numbers(numbers),)


class _LetterSuffixedVersion(SimulatorVersion):
    _pattern: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<release>\d+(?:\.\d+)*)(?P<letter>[a-z]?)(?:_(?P<patch>\d+))?",
        re.IGNORECASE,
    )

    @classmethod
    def _parse(cls, vstring: str) -> tuple[object, ...]:
        match = cls._pattern.search(vstring)
        if not match:
            raise ValueError(f"Unable to parse {cls.__name__} from: {vstring}")
        release = tuple(int(part) for part in match.group("release").split("."))
        letter = match.group("letter") or ""
        patch = int(match.group("patch")) if match.group("patch") else 0
        return (_normalize_release_numbers(release), _letter_value(letter), patch)


class ActivehdlVersion(_LetterSuffixedVersion):
    """Version numbering class for Aldec Active-HDL.

    NOTE: unsupported versions exist, e.g.
    ActivehdlVersion("10.5a.12.6914") > ActivehdlVersion("10.5.216.6767")
    """

    command = ("vsimsa", "-version")


class CvcVersion(_LetterSuffixedVersion):
    """Version numbering class for Tachyon DA CVC.

    Example:
        >>> CvcVersion(
        ...     "OSS_CVC_7.00b-x86_64-rhel6x of 07/07/14 (Linux-elf)"
        ... ) > CvcVersion("OSS_CVC_7.00a-x86_64-rhel6x of 07/07/14 (Linux-elf)")
        True
    """


class GhdlVersion(SimulatorVersion):
    """Version numbering class for GHDL."""

    command = ("ghdl", "--version")
    _pattern: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<release>\d+(?:\.\d+)*)(?P<suffix>[- ]?(?:dev|devel|rc\d*))?",
        re.IGNORECASE,
    )

    @classmethod
    def _extract_version_from_commandline(cls, cmdline: str) -> str:
        firstline = cmdline.strip().splitlines()[0]
        if firstline.lower().startswith("ghdl "):
            return firstline.split(" ", 1)[1]
        return firstline

    @classmethod
    def _parse(cls, vstring: str) -> tuple[object, ...]:
        match = cls._pattern.search(vstring)
        if not match:
            raise ValueError(f"Unable to parse GHDL version from: {vstring}")
        release = tuple(int(part) for part in match.group("release").split("."))
        suffix = (match.group("suffix") or "").lower()
        prerelease = -1 if suffix else 0
        return (_normalize_release_numbers(release), prerelease, suffix)


class IcarusVersion(SimulatorVersion):
    """Version numbering class for Icarus Verilog.

    Example:
        >>> IcarusVersion("11.0 (devel)") > IcarusVersion("10.3 (stable)")
        True
        >>> IcarusVersion("10.3 (stable)") <= IcarusVersion("10.3 (stable)")
        True
    """

    command = ("iverilog", "-V")
    _sim_pattern: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<release>\d+(?:\.\d+)*)(?:\s*\((?P<tag>[^)]+)\))?",
        re.IGNORECASE,
    )
    _cmd_pattern: ClassVar[re.Pattern[str]] = re.compile(
        r"^Icarus Verilog version (?P<version>\d+(?:\.\d+)*(?:\s*\([^)]+\))?)$",
        re.IGNORECASE,
    )
    _tag_order: ClassVar[dict[str, int]] = {"devel": -1, "stable": 0}

    @classmethod
    def _extract_version_from_commandline(cls, cmdline: str) -> str:
        firstline = cmdline.strip().splitlines()[0]
        match = cls._cmd_pattern.match(firstline)
        if not match:
            raise ValueError(
                f"Unable to parse Icarus Verilog version from: {firstline}"
            )
        return match.group("version")

    @classmethod
    def _parse(cls, vstring: str) -> tuple[object, ...]:
        match = cls._sim_pattern.search(vstring)
        if not match:
            raise ValueError(f"Unable to parse Icarus Verilog version from: {vstring}")
        release = tuple(int(part) for part in match.group("release").split("."))
        tag = (match.group("tag") or "").strip().lower()
        tag_order = cls._tag_order.get(tag, 0)
        return (_normalize_release_numbers(release), tag_order, tag)


class ModelsimVersion(_LetterSuffixedVersion):
    """Version numbering class for Mentor ModelSim."""

    command = ("vsim", "-version")


class QuestaVersion(_LetterSuffixedVersion):
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

    command = ("vsim", "-version")


class RivieraVersion(_SimpleDottedVersion):
    """Version numbering class for Aldec Riviera-PRO.

    Example:
        >>> RivieraVersion("2019.10.138.7537") == RivieraVersion("2019.10.138.7537")
        True
    """

    command = ("vsimsa", "-version")


class VcsVersion(SimulatorVersion):
    """Version numbering class for Synopsys VCS.

    Example:
        >>> VcsVersion("Q-2020.03-1_Full64") > VcsVersion("K-2015.09_Full64")
        True
    """

    _pattern: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<train>[A-Z])-(?P<year>\d{4})\.(?P<month>\d{2})(?:-(?P<patch>\d+))?",
    )

    @classmethod
    def _parse(cls, vstring: str) -> tuple[object, ...]:
        match = cls._pattern.search(vstring)
        if not match:
            raise ValueError(f"Unable to parse VCS version from: {vstring}")
        return (
            _letter_value(match.group("train")),
            int(match.group("year")),
            int(match.group("month")),
            int(match.group("patch")) if match.group("patch") else 0,
        )


class VerilatorVersion(SimulatorVersion):
    """Version numbering class for Verilator.

    Example:
        >>> VerilatorVersion("4.032 2020-04-04") > VerilatorVersion("4.031 devel")
        True
    """

    command = ("verilator", "--version")
    _sim_pattern: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<release>\d+(?:\.\d+)*)(?:\s+(?P<tag>devel))?",
        re.IGNORECASE,
    )
    _cmd_pattern: ClassVar[re.Pattern[str]] = re.compile(
        r"^Verilator\s+(?P<version>\d+(?:\.\d+)*(?:\s+devel)?)\b",
        re.IGNORECASE,
    )

    @classmethod
    def _extract_version_from_commandline(cls, cmdline: str) -> str:
        firstline = cmdline.strip().splitlines()[0]
        match = cls._cmd_pattern.match(firstline)
        if not match:
            raise ValueError(f"Unable to parse Verilator version from: {firstline}")
        return match.group("version")

    @classmethod
    def _parse(cls, vstring: str) -> tuple[object, ...]:
        match = cls._sim_pattern.search(vstring)
        if not match:
            raise ValueError(f"Unable to parse Verilator version from: {vstring}")
        release = tuple(int(part) for part in match.group("release").split("."))
        tag = (match.group("tag") or "").lower()
        prerelease = -1 if tag == "devel" else 0
        return (_normalize_release_numbers(release), prerelease)


class XceliumVersion(SimulatorVersion):
    """Version numbering class for Cadence Xcelium.

    Example:
        >>> XceliumVersion("20.06-g183") > XceliumVersion("20.03-s002")
        True
        >>> XceliumVersion("20.07-e501") > XceliumVersion("20.06-g183")
        True
    """

    command = ("xrun", "--version")
    _pattern: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<release>\d+(?:\.\d+)*)(?:-(?P<stream>[a-z])(?P<patch>\d+))?",
        re.IGNORECASE,
    )

    @classmethod
    def _parse(cls, vstring: str) -> tuple[object, ...]:
        match = cls._pattern.search(vstring)
        if not match:
            raise ValueError(f"Unable to parse Xcelium version from: {vstring}")
        release = tuple(int(part) for part in match.group("release").split("."))
        stream = match.group("stream") or ""
        patch = int(match.group("patch")) if match.group("patch") else 0
        return (_normalize_release_numbers(release), _letter_value(stream), patch)


class IusVersion(XceliumVersion):  # inherit everything from Xcelium
    """Version numbering class for Cadence IUS.

    Example:
        >>> IusVersion("15.20-s050") > IusVersion("15.20-s049")
        True
    """


class NvcVersion(_SimpleDottedVersion):
    """Version numbering class for NVC."""

    command = ("nvc", "--version")
    _cmd_pattern: ClassVar[re.Pattern[str]] = re.compile(
        r"^nvc\s+(?P<version>\d+(?:\.\d+)*)\b",
        re.IGNORECASE,
    )

    @classmethod
    def _extract_version_from_commandline(cls, cmdline: str) -> str:
        firstline = cmdline.strip().splitlines()[0]
        match = cls._cmd_pattern.match(firstline)
        if not match:
            raise ValueError(f"Unable to parse NVC version from: {firstline}")
        return match.group("version")
