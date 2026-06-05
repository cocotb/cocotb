# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Functions for detecting and managing HDL simulators in the system."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from shutil import which

from cocotb_tools.runner import (
    SUPPORTED_RUNNERS,
    VHDL,
    PathLike,
    Runner,
    VerilatorControlFile,
    Verilog,
)

#: Map name of HDL simulator to name of executable used by that HDL simulator.
#: If HDL simulator is not present in this dictionary, it means that name of HDL simulator == name of executable.
_SIMULATOR_TO_TOOL: dict[str, str] = {
    "icarus": "iverilog",
    "xcelium": "xrun",
    "questa": "vsim",
    "riviera": "vsimsa",
}

#: Map file extension suffix to language.
_SUFFIX_TO_LANGUAGE: dict[str, str] = {
    ".v": "verilog",
    ".sv": "verilog",
    ".vhd": "vhdl",
    ".vhdl": "vhdl",
}


def detect_language(
    source: PathLike | VHDL | Verilog | VerilatorControlFile,
) -> str | None:
    """Detect the hardware description language of the provided source file.

    Args:
        source: The source file path.

    Returns:
        ``"verilog"`` if the source file is Verilog or SystemVerilog,
        ``"vhdl"`` if the source file is VHDL,
        or :data:`None` if the language cannot be determined.
    """
    if isinstance(source, Verilog):
        return "verilog"

    if isinstance(source, VHDL):
        return "vhdl"

    if not isinstance(source, Path):
        source = Path(str(source))

    return _SUFFIX_TO_LANGUAGE.get(source.suffix)


def detect_languages(
    sources: Iterable[PathLike | VHDL | Verilog | VerilatorControlFile],
) -> set[str]:
    """Detect all hardware description languages from the provided list of source files.

    Args:
        sources: An iterable of source files.

    Returns:
        A set of detected language strings (e.g., ``{"verilog", "vhdl"}``).
    """
    return set(filter(None, map(detect_language, sources)))


def get_supported_languages(simulator: str | None) -> list[str]:
    """Get list of supported languages by the HDL simulator.

    Args:
        simulator: Name of the HDL simulator.

    Returns:
        List of supported languages by the HDL simulator.
    """
    if not simulator:
        return []

    runner: type[Runner] | None = SUPPORTED_RUNNERS.get(simulator)

    return list(runner.supported_gpi_interfaces) if runner else []


def are_languages_supported(
    simulator: str | None, languages: Iterable[str] | str | None
) -> bool:
    """Check if the provided languages are supported by the HDL simulator.

    Args:
        simulator: Name of the HDL simulator.
        languages: A list or single string of languages (e.g., ``"verilog"``, ``"vhdl"``) to check.

    Returns:
        :data:`True` if all specified languages are supported by the HDL simulator; otherwise, :data:`False`.
    """
    if not languages or languages == "auto":
        return True

    supported_languages: list[str] = get_supported_languages(simulator)

    if isinstance(languages, str):
        return languages in supported_languages

    for language in languages:
        if language not in supported_languages:
            return False

    return True


def is_simulator_available(name: str) -> bool:
    """Check if the specified HDL simulator is available in the system ``PATH``.

    Args:
        name: The name of the HDL simulator to check.

    Returns:
        :data:`True` if the simulator's executable is found; otherwise, :data:`False`.
    """
    return which(_SIMULATOR_TO_TOOL.get(name, name)) is not None


def find_simulator(languages: Iterable[str] | str | None = None) -> str | None:
    """Find the most suitable HDL simulator in the current environment that supports the requested languages.

    Args:
        languages: The required language(s) that the simulator must support.

    Returns:
        The name of the detected simulator if found; otherwise, :data:`None`.
    """
    for name in SUPPORTED_RUNNERS:
        if are_languages_supported(name, languages) and is_simulator_available(name):
            return name

    return None
