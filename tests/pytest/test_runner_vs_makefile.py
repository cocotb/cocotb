# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import pytest

import cocotb
from cocotb.clock import Clock
from cocotb.runner import get_runner
from cocotb.triggers import ClockCycles, RisingEdge

tests_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root_dir = os.path.dirname(tests_dir)

sys.path.insert(0, os.path.join(tests_dir, "pytest"))

# Cocotb test


@cocotb.test()
async def cocotb_basic_hierarchy_design_test(dut) -> None:
    cocotb.start_soon(Clock(dut.clk, 10).start())
    dut.reset.setimmediatevalue(0)
    await RisingEdge(dut.clk)
    dut.reset.value = 1
    await ClockCycles(dut.clk, 10)


# Auxiliary types

Command = List[str]
Options = Dict[str, List[str]]

# Auxiliary functions


def read_file_lines(path) -> Sequence[str]:
    """Reads file and returns its contents as sequence of lines"""
    with open(path) as f:
        return f.readlines()


def get_line_with_exec_name(make_log, exec_name) -> Sequence[str]:
    """Extracts the lines with the name of the executable from the multiline string"""

    match = re.search(f"(^.*{exec_name}.*$)", make_log, flags=re.MULTILINE)
    return match.groups()


def exec_make_flow_and_get_cmds(
    sim: str,
    verilog_sources: List[str],
    hdl_toplevel: str,
    hdl_toplevel_lang: str,
    module: str,
    waves: bool,
    clean: bool = True,
) -> str:
    """Executes Cocotb make flow and returns commands used to launch a simulator"""
    makefile_path = f"{__name__}.Makefile"
    with open(makefile_path, "w") as f:
        f.write(f"COCOTB := {root_dir}\n")
        f.write(f"SIM := {sim}\n")
        f.write(f"VERILOG_SOURCES := {' '.join(verilog_sources)}\n")
        f.write(f"TOPLEVEL := {hdl_toplevel}\n")
        f.write(f"TOPLEVEL_LANG := {hdl_toplevel_lang}\n")
        f.write(f"MODULE := {module}\n")
        f.write(f"WAVES := {1 if waves else 0}\n")
        f.write("include $(shell cocotb-config --makefiles)/Makefile.sim\n")

    if clean:
        subprocess.check_call(f"make --file {makefile_path} clean", shell=True)

    make_cmd = f"PYTHONPATH={os.path.dirname(__file__)} make --file {makefile_path} --always-make"
    make_log = subprocess.check_output(make_cmd, shell=True)
    os.remove(makefile_path)

    return make_log.decode("utf-8")


def exec_runner_flow_and_get_cmds(
    sim: str,
    verilog_sources: List[str],
    hdl_toplevel: str,
    hdl_toplevel_lang: str,
    module: str,
    waves: bool,
    clean: bool,
) -> Tuple[Sequence[Command], Sequence[Command]]:
    """Executes Cocotb runner flow and returns build and test commands"""
    runner = get_runner(sim)
    runner.build(
        hdl_toplevel=hdl_toplevel,
        verilog_sources=verilog_sources,
        always=True,
        clean=clean,
        waves=waves,
    )
    build_cmds = runner._build_command()

    runner.test(
        hdl_toplevel=hdl_toplevel,
        hdl_toplevel_lang=hdl_toplevel_lang,
        test_module=module,
    )
    test_cmds = runner._test_command()

    return build_cmds, test_cmds


def check_make_and_runner_cmd(
    make_cmd: Command, runner_cmd: Command, options: Options
) -> None:
    assert_msg = (
        "Commands executed in the runner and makefile flows differ:\n"
        f"{' '.join(make_cmd)} \n!=\n {' '.join(runner_cmd)}\n"
    )
    it = enumerate(zip(make_cmd, runner_cmd))
    for i, (make_part, runner_part) in enumerate(zip(make_cmd, runner_cmd)):
        if i == 0:  # executable
            make_exec_name = os.path.basename(make_part)
            runner_exec_name = os.path.basename(runner_part)

            assert make_exec_name == runner_exec_name, assert_msg
        elif make_part in options["normal"]:
            assert make_part == runner_part, assert_msg
        elif make_part in options["with_paths"]:
            # Build invocation from a runner interface uses absolute paths,
            # while building from the Makefiles uses relative paths
            # Because of that the paths needs to be resolved before comparison
            make_part_path = Path(make_cmd[i + 1]).resolve()
            runner_part_path = Path(runner_cmd[i + 1]).resolve()

            assert make_part == runner_part, assert_msg
            assert make_part_path == runner_part_path, assert_msg
            next(it)
        elif make_part in options["with_no_paths"]:
            assert make_part == runner_part, assert_msg
            assert make_cmd[i + 1] == runner_cmd[i + 1], assert_msg
            next(it)
        else:  # sources
            # Build invocation from a runner interface uses absolute paths,
            # while building from the Makefiles uses relative paths
            # Because of that the paths needs to be resolved before comparison
            make_part_path = Path(make_part).resolve()
            runner_part_path = Path(runner_part).resolve()
            assert make_part_path == runner_part_path, assert_msg


# Icarus-specific functions


def exec_icarus_make_flow_and_get_cmds(
    sim: str,
    verilog_sources: List[str],
    hdl_toplevel: str,
    hdl_toplevel_lang: str,
    module: str,
    waves: bool,
    clean: bool,
) -> Tuple[Sequence[Command], Sequence[Command]]:
    """Executes Cocotb make flow for Icarus simulator and returns commands
    used to launch Iverilog and VVP"""
    make_log = exec_make_flow_and_get_cmds(
        sim, verilog_sources, hdl_toplevel, hdl_toplevel_lang, module, waves, clean
    )
    vvp_cmds, iverilog_cmds = [
        get_line_with_exec_name(make_log, shutil.which(x)) for x in ["vvp", "iverilog"]
    ]

    iverilog_cmds = [cmd.split() for cmd in iverilog_cmds]
    vvp_cmds = [cmd.split() for cmd in vvp_cmds]

    return iverilog_cmds, vvp_cmds


def check_iverilog_cmd(make_cmd: Command, runner_cmd: Command) -> None:
    # fmt:off
    options: Options = {
        "normal": [
            "-E", "-i", "-S", "-u", "-v", "-V",
            "-g1995", "-g2001", "-g2005", "-g2005-sv", "-g2009", "-g2012",
        ],
        "with_paths": ["-c", "-f", "-I", "-L", "-M", "-N", "-o", "-y", "-l"],
        "with_no_paths": ["-B", "-D", "-m", "-p", "-s", "-t", "-T", "-W", "-Y"],
    }  # fmt:on
    check_make_and_runner_cmd(make_cmd, runner_cmd, options)


def check_vvp_cmd(make_cmd: Command, runner_cmd: Command) -> None:
    options: Options = {
        "normal": ["-h", "-i", "-n", "-N", "-s", "-v", "-V"],
        "with_paths": ["-l", "-M"],
        "with_no_paths": ["-m"],
    }
    check_make_and_runner_cmd(make_cmd, runner_cmd, options)


def check_cmds_contents(make_contents, runner_contents):
    assert len(make_contents) == len(runner_contents)
    for i in range(len(make_contents)):
        assert make_contents[i] == runner_contents[i]


def check_cocotb_iverilog_dump_contents(make_contents, runner_contents):
    def get_dumpfile_path(line: str):
        (path,) = re.search(r"dumpfile\(\"(.*)\"\);", line).groups()
        return path

    for i, line in enumerate(make_contents):
        if "dumpfile" in line:
            make_path = get_dumpfile_path(make_contents[i])
            runner_path = get_dumpfile_path(runner_contents[i])

            assert make_path is not None and runner_path is not None
            assert Path(make_path).resolve() == Path(runner_path).resolve()
        else:
            assert line == runner_contents[i]


# test cases


@pytest.mark.simulator_required
@pytest.mark.skipif(
    os.getenv("SIM", "icarus") != "icarus",
    reason="Skipping test because it is only for Icarus simulator",
)
@pytest.mark.parametrize("waves", [False, True])
def test_iverilog(waves) -> None:
    """Checks if the commands executed in the makefile flow are the same as
    in the runner flow for Icarus simulator"""
    sim = "icarus"
    clean = True
    module = "test_runner_vs_makefile"
    hdl_toplevel_lang = "verilog"
    hdl_toplevel = "basic_hierarchy_module"
    verilog_sources = [
        f"{tests_dir}/designs/basic_hierarchy_module/basic_hierarchy_module.v"
    ]

    CMDS_FILE = "sim_build/cmds.f"
    COCOTB_IVERILOG_DUMP_FILE = "sim_build/cocotb_iverilog_dump.v"

    cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as dirpath:
            os.chdir(dirpath)

            # Makefile flow

            make_iverilog_cmds, make_vvp_cmds = exec_icarus_make_flow_and_get_cmds(
                sim,
                verilog_sources,
                hdl_toplevel,
                hdl_toplevel_lang,
                module,
                waves,
                clean,
            )
            assert len(make_iverilog_cmds) == 1
            assert len(make_vvp_cmds) == 1

            make_cmds_contents = read_file_lines(CMDS_FILE)
            if waves:
                make_iverilog_dump_contents = read_file_lines(COCOTB_IVERILOG_DUMP_FILE)

            # Runner flow

            runner_iverilog_cmds, runner_vvp_cmds = exec_runner_flow_and_get_cmds(
                sim,
                verilog_sources,
                hdl_toplevel,
                hdl_toplevel_lang,
                module,
                waves,
                clean,
            )
            assert len(runner_iverilog_cmds) == 1
            assert len(runner_vvp_cmds) == 1

            runner_cmds_contents = read_file_lines(CMDS_FILE)
            if waves:
                runner_iverilog_dump_contents = read_file_lines(
                    COCOTB_IVERILOG_DUMP_FILE
                )

            # Checks

            check_vvp_cmd(make_vvp_cmds[0], runner_vvp_cmds[0])
            check_iverilog_cmd(make_iverilog_cmds[0], runner_iverilog_cmds[0])

            check_cmds_contents(make_cmds_contents, runner_cmds_contents)
            if waves:
                check_cocotb_iverilog_dump_contents(
                    make_iverilog_dump_contents, runner_iverilog_dump_contents
                )

    except Exception:
        raise
    finally:
        os.chdir(cwd)
