# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""Build-time version provider implementing the dynamic-metadata protocol."""

from __future__ import annotations

import re
import subprocess
from email.parser import HeaderParser
from pathlib import Path
from typing import TYPE_CHECKING, Any

from packaging.version import InvalidVersion, Version

if TYPE_CHECKING:
    from collections.abc import Mapping

ARCHIVAL_FILE = ".git_archival.txt"


def _git(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args], capture_output=True, text=True, check=False
        )
    except FileNotFoundError:
        return ""
    return result.stdout if result.returncode == 0 else ""


def _archive_version(path: Path) -> str | None:
    if not path.is_file():
        return None
    data = HeaderParser().parsestr(path.read_text(encoding="utf-8"))
    if any("$Format" in value for value in data.values()):
        return None

    # Our archives use %D for both fields; also accept a git describe result
    # carrying a commit count, as setuptools-git-versioning does.
    describe = data.get("describe-name", "").strip()
    tags = re.findall(r"(?:^|,\s*)tag:\s*([^,]+)", data.get("ref-names", ""))
    dirty = describe.endswith("-dirty")
    if dirty:
        describe = describe.removesuffix("-dirty")
    match = re.fullmatch(r"(.+)-(\d+)-g([0-9a-f]+)", describe)
    if tags:
        version = tags[0].strip()
    elif match:
        version, count, sha = match.groups()
        node = data.get("node", "").strip()
        if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", node):
            sha = node
        if int(count):
            version = f"{version}.dev{int(count)}+r{sha[:8]}"
    else:
        version = describe
    try:
        version = str(Version(version))
    except InvalidVersion:
        return None
    if dirty:
        version += ".dirty" if "+" in version else "+dirty"
    return version


def dynamic_metadata(
    settings: Mapping[str, Any], project: Mapping[str, Any]
) -> dict[str, str]:
    """Resolve the version from an sdist, a Git archive, or the checkout."""
    root = Path.cwd()
    pkg_info = root / "PKG-INFO"
    if pkg_info.is_file():
        version = (
            HeaderParser().parsestr(pkg_info.read_text(encoding="utf-8")).get("Version")
        )
        if version:
            return {"version": str(Version(version))}

    archived_version = _archive_version(root / ARCHIVAL_FILE)
    if archived_version is not None:
        return {"version": archived_version}

    # Require the project's own repository so an unpacked source tree cannot
    # accidentally inherit the history and status of a parent repository.
    head = (
        _git("rev-parse", "--verify", "HEAD").strip()
        if (root / ".git").exists()
        else ""
    )
    status = _git("status", "--porcelain=v1", "-z") if head else ""
    tags = (
        _git("tag", "--points-at", "HEAD", "--sort=-creatordate").splitlines()
        if head
        else []
    )
    if tags:
        version = tags[0]
    else:
        version = (root / "VERSION").read_text(encoding="utf-8").strip()
        if head:
            count = 0
            if not any(entry[3:] == "VERSION" for entry in status.split("\0")):
                last_change = _git(
                    "log", "--first-parent", "-1", "--format=%H", "--", "VERSION"
                ).strip()
                if last_change:
                    count = int(
                        _git(
                            "rev-list",
                            "--first-parent",
                            "--count",
                            f"{last_change}..HEAD",
                        )
                        or "0"
                    )
            version = f"{version}.dev{count}+r{head[:8]}"
    if status:
        version += ".dirty" if "+" in version else "+dirty"
    return {"version": str(Version(version))}
