# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""Exercise the build-time version provider using real Git repositories."""

from __future__ import annotations

import os
import runpy
import subprocess
import tarfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

SOURCE_ROOT = Path(__file__).resolve().parents[2]
dynamic_metadata = runpy.run_path(str(SOURCE_ROOT / "scripts" / "cocotb_version.py"))[
    "dynamic_metadata"
]


@pytest.fixture
def git_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[..., str]:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, check=True
        ).stdout.strip()

    git("init")
    git("symbolic-ref", "HEAD", "refs/heads/main")
    git("config", "user.name", "Version tests")
    git("config", "user.email", "version-tests@example.com")
    Path("VERSION").write_text("2.2.0\n", encoding="utf-8")
    Path(".gitignore").write_text("ignored\n", encoding="utf-8")
    for name in (".git_archival.txt", ".gitattributes"):
        Path(name).write_bytes((SOURCE_ROOT / name).read_bytes())
    git("add", ".")
    git("commit", "-m", "Set VERSION")
    return git


def test_version_change_commit(git_repo: Callable[..., str]) -> None:
    sha = git_repo("rev-parse", "HEAD")[:8]
    assert dynamic_metadata({}, {})["version"] == f"2.2.0.dev0+r{sha}"


def test_first_parent_count(git_repo: Callable[..., str]) -> None:
    git_repo("checkout", "-b", "side")
    for _ in range(3):
        git_repo("commit", "--allow-empty", "-m", "Side change")
    git_repo("checkout", "main")
    git_repo("commit", "--allow-empty", "-m", "Main change")
    git_repo("merge", "--no-ff", "side", "-m", "Merge side")
    sha = git_repo("rev-parse", "HEAD")[:8]
    assert dynamic_metadata({}, {})["version"] == f"2.2.0.dev2+r{sha}"


def test_version_change_on_merge(git_repo: Callable[..., str]) -> None:
    git_repo("checkout", "-b", "side")
    Path("VERSION").write_text("2.3.0\n", encoding="utf-8")
    git_repo("commit", "-am", "Bump VERSION")
    git_repo("checkout", "main")
    git_repo("commit", "--allow-empty", "-m", "Main change")
    git_repo("merge", "--no-ff", "side", "-m", "Merge VERSION change")
    sha = git_repo("rev-parse", "HEAD")[:8]
    assert dynamic_metadata({}, {})["version"] == f"2.3.0.dev0+r{sha}"


@pytest.mark.parametrize(
    "tag",
    ["v2.2.0", "v2.2.0rc1", "v2.2.0.dev7", "v2.2.0.post1", "v2.2.0+build", "v9.8.10"],
)
def test_exact_tag(git_repo: Callable[..., str], tag: str) -> None:
    git_repo("commit", "--allow-empty", "-m", "Change")
    git_repo("tag", tag)
    assert dynamic_metadata({}, {})["version"] == tag.removeprefix("v")


def test_previous_tag_does_not_override_version(git_repo: Callable[..., str]) -> None:
    git_repo("tag", "v2.1.0")
    git_repo("commit", "--allow-empty", "-m", "Change")
    sha = git_repo("rev-parse", "HEAD")[:8]
    assert dynamic_metadata({}, {})["version"] == f"2.2.0.dev1+r{sha}"


@pytest.mark.parametrize("tagged", [False, True])
@pytest.mark.parametrize("change", ["untracked", "modified", "staged", "deleted"])
def test_dirty_checkout(
    git_repo: Callable[..., str], tagged: bool, change: str
) -> None:
    if tagged:
        git_repo("tag", "v2.2.0rc1")
    if change == "untracked":
        Path("untracked").write_text("new file\n", encoding="utf-8")
    elif change == "deleted":
        git_repo("rm", ".gitignore")
    else:
        Path(".gitattributes").write_text("# changed\n", encoding="utf-8")
        if change == "staged":
            git_repo("add", ".gitattributes")
    sha = git_repo("rev-parse", "HEAD")[:8]
    expected = "2.2.0rc1+dirty" if tagged else f"2.2.0.dev0+r{sha}.dirty"
    assert dynamic_metadata({}, {})["version"] == expected


def test_ignored_files_are_clean(git_repo: Callable[..., str]) -> None:
    Path("ignored").write_text("ignored file\n", encoding="utf-8")
    sha = git_repo("rev-parse", "HEAD")[:8]
    assert dynamic_metadata({}, {})["version"] == f"2.2.0.dev0+r{sha}"


@pytest.mark.parametrize("staged", [False, True])
@pytest.mark.parametrize("tagged", [False, True])
def test_working_version_resets_count(
    git_repo: Callable[..., str], staged: bool, tagged: bool
) -> None:
    git_repo("commit", "--allow-empty", "-m", "Change")
    if tagged:
        git_repo("tag", "v2.2.0rc1")
    Path("VERSION").write_text("2.3.0\n", encoding="utf-8")
    if staged:
        git_repo("add", "VERSION")
    sha = git_repo("rev-parse", "HEAD")[:8]
    expected = "2.2.0rc1+dirty" if tagged else f"2.3.0.dev0+r{sha}.dirty"
    assert dynamic_metadata({}, {})["version"] == expected


def test_dirty_tag_with_local_version(git_repo: Callable[..., str]) -> None:
    git_repo("tag", "v2.2.0+build")
    Path("untracked").touch()
    assert dynamic_metadata({}, {})["version"] == "2.2.0+build.dirty"


@pytest.mark.parametrize("depth", [1, 2])
def test_shallow_clone(
    git_repo: Callable[..., str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    depth: int,
) -> None:
    for _ in range(3):
        git_repo("commit", "--allow-empty", "-m", "Change")
    sha = git_repo("rev-parse", "HEAD")[:8]
    clone = tmp_path / "clone"
    git_repo("clone", "--depth", str(depth), tmp_path.as_uri(), str(clone))
    monkeypatch.chdir(clone)
    assert dynamic_metadata({}, {})["version"] == f"2.2.0.dev{depth - 1}+r{sha}"


def test_worktree(
    git_repo: Callable[..., str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    git_repo("commit", "--allow-empty", "-m", "Change")
    sha = git_repo("rev-parse", "HEAD")[:8]
    worktree = tmp_path / "worktree"
    git_repo("worktree", "add", "--detach", str(worktree), "HEAD")
    monkeypatch.chdir(worktree)
    assert dynamic_metadata({}, {})["version"] == f"2.2.0.dev1+r{sha}"


def test_source_copy_inside_repository(
    git_repo: Callable[..., str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source-copy"
    source.mkdir()
    (source / "VERSION").write_text("2.3.0\n", encoding="utf-8")
    monkeypatch.chdir(source)
    assert dynamic_metadata({}, {})["version"] == "2.3.0"


def test_git_unavailable(
    git_repo: Callable[..., str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", "")
    assert dynamic_metadata({}, {})["version"] == "2.2.0"


@pytest.mark.parametrize("describe", [False, True])
@pytest.mark.parametrize("commits", [0, 3])
def test_git_archive(
    git_repo: Callable[..., str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    describe: bool,
    commits: int,
) -> None:
    if describe:
        if (
            git_repo("log", "-1", "--format=%(describe:tags=true)")
            == "%(describe:tags=true)"
        ):
            pytest.skip("Git does not support %(describe:tags=true)")
        archival = Path(".git_archival.txt")
        archival.write_text(
            archival.read_text(encoding="utf-8").replace(
                "describe-name: $Format:%D$",
                "describe-name: $Format:%(describe:tags=true)$",
            ),
            encoding="utf-8",
        )
        git_repo("commit", "-am", "Include describe information")
    git_repo("tag", "v2.2.0rc1")
    for _ in range(commits):
        git_repo("commit", "--allow-empty", "-m", "Change")
    sha = git_repo("rev-parse", "HEAD")[:8]
    archive = tmp_path / "archive.tar"
    git_repo("archive", "--format=tar", f"--output={archive}", "HEAD")
    source = tmp_path / "archive"
    source.mkdir()
    with tarfile.open(archive) as tar:
        for name in ("VERSION", ".git_archival.txt"):
            member = tar.extractfile(name)
            assert member is not None
            (source / name).write_bytes(member.read())
    monkeypatch.chdir(source)
    expected = (
        "2.2.0rc1"
        if commits == 0
        else (f"2.2.0rc1.dev3+r{sha}" if describe else "2.2.0")
    )
    assert dynamic_metadata({}, {})["version"] == expected


@pytest.mark.parametrize(
    "archival",
    [
        "describe-name: $Format:%D$\n",
        "describe-name: %(describe:tags=true)\nref-names: main\n",
        "describe-name: HEAD -> main\nref-names: HEAD -> main\n",
        "node: deadbeef\n",
    ],
)
def test_archive_without_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, archival: str
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("VERSION").write_text("2.2.0\n", encoding="utf-8")
    Path(".git_archival.txt").write_text(archival, encoding="utf-8")
    assert dynamic_metadata({}, {})["version"] == "2.2.0"


@pytest.mark.parametrize(
    ("describe", "refs", "expected"),
    [
        ("v2.2.0-3-gdeadbeef-dirty", "", "2.2.0.dev3+rdeadbeef.dirty"),
        ("v2.2.0-0-gdeadbeef-dirty", "", "2.2.0+dirty"),
        ("v2.1.0-3-gdeadbeef-dirty", "tag: v2.2.0rc1", "2.2.0rc1+dirty"),
    ],
)
def test_archive_with_dirty_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    describe: str,
    refs: str,
    expected: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".git_archival.txt").write_text(
        f"describe-name: {describe}\nref-names: {refs}\n", encoding="utf-8"
    )
    assert dynamic_metadata({}, {})["version"] == expected


def test_pkg_info_preserves_version(git_repo: Callable[..., str]) -> None:
    git_repo("tag", "v2.2.0")
    Path("VERSION").write_text("2.3.0\n", encoding="utf-8")
    Path("PKG-INFO").write_text(
        "Metadata-Version: 2.2\nName: cocotb\nVersion: 2.1.0.dev7+rdeadbeef.dirty\n",
        encoding="utf-8",
    )
    assert dynamic_metadata({}, {})["version"] == "2.1.0.dev7+rdeadbeef.dirty"
