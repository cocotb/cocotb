# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pexpect
import pytest

if sys.platform != "win32":
    from pexpect import spawn

pytestmark = pytest.mark.simulator_required

tests_dir = Path(__file__).resolve().parent.parent
sample_module_dir = tests_dir / "designs" / "sample_module"
sim = os.getenv(
    "SIM",
    "icarus" if os.getenv("TOPLEVEL_LANG", "verilog") == "verilog" else "nvc",
)


def spawn_make(env: dict[str, str]):
    return spawn(
        "make",
        ["-C", str(sample_module_dir)],
        env=env,
        encoding="utf-8",
        timeout=90,
    )


def terminate_child(child) -> None:
    if hasattr(child, "proc"):
        if child.proc.poll() is None:
            child.proc.terminate()
            try:
                child.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.proc.kill()
                child.proc.wait()
    elif child.isalive():
        child.terminate(force=True)


def assert_child_exited(child) -> None:
    if hasattr(child, "proc"):
        assert child.wait() == 0
    else:
        assert child.exitstatus == 0


@pytest.mark.skipif(
    sim not in ["icarus", "verilator", "ghdl", "nvc", "xcelium"],
    reason="Skipping test because it requires direct access to simulator output",
)
@pytest.mark.skipif(
    sys.platform == "win32",
    reason="pexpect.spawn is not available on Windows",
)
def test_ipython_support_interactive(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.update(
        {
            "COCOTB_ANSI_OUTPUT": "0",
            "COCOTB_TEST_MODULES": "cocotb_tools.ipython_support",
            "IPYTHONDIR": str(tmp_path / "ipython"),
            "PATH": os.pathsep.join(
                [str(Path(sys.executable).parent), os.environ.get("PATH", "")]
            ),
            "TERM": "dumb",
        }
    )

    subprocess.run(
        ["make", "-C", str(sample_module_dir), "clean"],
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    child = spawn_make(env)
    try:
        child.expect(r"In \[1\]:")

        child.sendline("print(dut._name)")
        child.expect("sample_module")
        child.expect(r"In \[2\]:")

        child.sendline("import cocotb")
        child.expect(r"In \[3\]:")

        child.sendline("from cocotb.triggers import Timer")
        child.expect(r"In \[4\]:")

        child.sendline('await Timer(1, "ns")')
        child.expect(r"In \[5\]:")

        child.sendline("exit()")
        child.expect(pexpect.EOF)
    finally:
        terminate_child(child)

    assert_child_exited(child)
