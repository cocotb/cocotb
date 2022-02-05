# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import abc
import os
import re
import shutil
import subprocess
import sys
import tempfile
import warnings
from contextlib import suppress
from typing import Dict, List, Mapping, Optional, Sequence, Type, Union
from xml.etree import cElementTree as ET

import cocotb.config

PathLike = Union["os.PathLike[str]", str]
Command = List[str]

warnings.warn(
    "Python runners and associated APIs are an experimental feature and subject to change.",
    UserWarning,
    stacklevel=2,
)

_magic_re = re.compile(r"([\\{}])")
_space_re = re.compile(r"([\s])", re.ASCII)


def as_tcl_value(value: str) -> str:
    # add '\' before special characters and spaces
    value = _magic_re.sub(r"\\\1", value)
    value = value.replace("\n", r"\n")
    value = _space_re.sub(r"\\\1", value)
    if value[0] == '"':
        value = "\\" + value

    return value


class Simulator(abc.ABC):
    def __init__(self) -> None:

        self.simulator_in_path()

        self.env: Dict[str, str] = {}

        # for running test() independently of build()
        self.build_dir = "sim_build"
        self.parameters = {}

    @abc.abstractmethod
    def simulator_in_path(self) -> None:
        """Check that the simulator executable exists in `PATH`."""

        raise NotImplementedError()

    @abc.abstractmethod
    def check_toplevel_lang(self, toplevel_lang: Optional[str]) -> str:
        """Return *toplevel_lang* if supported by simulator, raise exception otherwise."""

        raise NotImplementedError()

    def set_env(self) -> None:
        """Set environment variables for sub-processes."""

        for e in os.environ:
            self.env[e] = os.environ[e]

        if "LIBPYTHON_LOC" not in self.env:
            self.env["LIBPYTHON_LOC"] = cocotb._vendor.find_libpython.find_libpython()

        self.env["PATH"] += os.pathsep + cocotb.config.libs_dir

        self.env["PYTHONPATH"] = os.pathsep.join(sys.path)
        for path in self.python_search:
            self.env["PYTHONPATH"] += os.pathsep + str(path)

        self.env["PYTHONHOME"] = sys.prefix

        self.env["TOPLEVEL"] = self.sim_toplevel
        self.env["MODULE"] = self.module

    @abc.abstractmethod
    def build_command(self) -> Sequence[Command]:
        """Return command to build the HDL sources."""

        raise NotImplementedError()

    @abc.abstractmethod
    def test_command(self) -> Sequence[Command]:
        """Return command to run a test."""

        raise NotImplementedError()

    def build(
        self,
        library_name: str = "work",
        verilog_sources: Sequence[PathLike] = [],
        vhdl_sources: Sequence[PathLike] = [],
        includes: Sequence[PathLike] = [],
        defines: Sequence[str] = [],
        parameters: Mapping[str, object] = {},
        extra_args: Sequence[str] = [],
        toplevel: Optional[str] = None,
        always: bool = False,
        build_dir: PathLike = "sim_build",
    ) -> None:
        """Build the HDL sources."""

        self.build_dir = os.path.abspath(build_dir)
        os.makedirs(self.build_dir, exist_ok=True)

        # note: to avoid mutating argument defaults, we ensure that no value
        # is written without a copy. This is much more concise and leads to
        # a better docstring than using `None` as a default in the parameters
        # list.
        self.library_name = library_name
        self.verilog_sources = get_abs_paths(verilog_sources)
        self.vhdl_sources = get_abs_paths(vhdl_sources)
        self.includes = get_abs_paths(includes)
        self.defines = list(defines)
        self.parameters = dict(parameters)
        self.compile_args = list(extra_args)
        self.always = always
        self.hdl_toplevel = toplevel

        for e in os.environ:
            self.env[e] = os.environ[e]

        cmds = self.build_command()
        self.execute(cmds, cwd=self.build_dir)

    def test(
        self,
        py_module: Union[str, Sequence[str]],
        toplevel: str,
        toplevel_lang: Optional[str] = None,
        testcase: Optional[str] = None,
        seed: Optional[Union[str, int]] = None,
        python_search: Sequence[PathLike] = [],
        extra_args: Sequence[str] = [],
        plus_args: Sequence[str] = [],
        extra_env: Mapping[str, str] = {},
        waves: Optional[bool] = None,
        gui: Optional[bool] = None,
        parameters: Mapping[str, object] = None,
        build_dir: Optional[PathLike] = None,
        sim_dir: Optional[PathLike] = None,
    ) -> PathLike:
        """Run a test."""

        __tracebackhide__ = True  # Hide the traceback when using pytest

        if build_dir is not None:
            self.build_dir = build_dir

        if parameters is not None:
            self.parameters = dict(parameters)

        if sim_dir is None:
            self.sim_dir = self.build_dir
        else:
            self.sim_dir = os.path.abspath(sim_dir)

        if isinstance(py_module, str):
            self.module = py_module
        else:
            self.module = ",".join(py_module)

        # note: to avoid mutating argument defaults, we ensure that no value
        # is written without a copy. This is much more concise and leads to
        # a better docstring than using `None` as a default in the parameters
        # list.
        self.python_search = list(python_search)
        self.sim_toplevel = toplevel
        self.toplevel_lang = self.check_toplevel_lang(toplevel_lang)
        self.sim_args = list(extra_args)
        self.plus_args = list(plus_args)
        self.env = dict(extra_env)

        if testcase is not None:
            self.env["TESTCASE"] = testcase

        if seed is not None:
            self.env["RANDOM_SEED"] = str(seed)

        if waves is None:
            self.waves = bool(int(os.getenv("COCOTB_WAVES", 0)))
        else:
            self.waves = bool(waves)

        if gui is None:
            self.gui = bool(int(os.getenv("COCOTB_GUI", 0)))
        else:
            self.gui = bool(gui)

        # When using pytest, use test name as result file name
        pytest_current_test = os.environ.get("PYTEST_CURRENT_TEST", "")

        if pytest_current_test:
            results_xml_name = (
                pytest_current_test.split(":")[-1].split(" ")[0] + ".results.xml"
            )
        else:
            results_xml_name = "results.xml"

        results_xml_file = os.getenv(
            "COCOTB_RESULTS_FILE", os.path.join(self.build_dir, results_xml_name)
        )

        self.env["COCOTB_RESULTS_FILE"] = results_xml_file

        with suppress(OSError):
            os.remove(results_xml_file)

        cmds = self.test_command()
        self.set_env()
        self.execute(cmds, cwd=self.sim_dir)

        check_results_file(results_xml_file)

        print(f"INFO: Results file: {results_xml_file}")
        return results_xml_file

    @abc.abstractmethod
    def get_include_options(self, includes: Sequence[str]) -> List[str]:
        """Return simulator options setting directories searched for Verilog include files."""

        raise NotImplementedError()

    @abc.abstractmethod
    def get_define_options(self, defines: Sequence[str]) -> List[str]:
        """Return simulator options defining macros."""

        raise NotImplementedError()

    @abc.abstractmethod
    def get_parameter_options(self, parameters: Mapping[str, object]) -> List[str]:
        """Return simulator options for module parameters/generics."""

        raise NotImplementedError()

    def execute(self, cmds: Sequence[Command], cwd: PathLike) -> None:

        __tracebackhide__ = True  # Hide the traceback when using PyTest.

        for cmd in cmds:
            print(
                "INFO: Running command: "
                + ' "'.join(cmd)
                + '" in directory:"'
                + str(cwd)
                + '"'
            )

            # TODO: create a thread to handle stderr and log as error?
            # TODO: log forwarding

            process = subprocess.run(cmd, cwd=cwd, env=self.env)

            if process.returncode != 0:
                raise SystemExit(
                    f"Process {process.args[0]!r} terminated with error {process.returncode}"
                )


def check_results_file(results_xml_file: PathLike) -> None:
    """Check whether cocotb result file exists and contains failed tests."""

    __tracebackhide__ = True  # Hide the traceback when using PyTest.

    results_file_exist = os.path.isfile(results_xml_file)
    if not results_file_exist:
        raise SystemExit(
            "ERROR: Simulation terminated abnormally. Results file not found."
        )

    failed = 0

    tree = ET.parse(results_xml_file)
    for ts in tree.iter("testsuite"):
        for tc in ts.iter("testcase"):
            for _ in tc.iter("failure"):
                failed += 1

    if failed:
        raise SystemExit(f"ERROR: Failed {failed} tests.")


def outdated(output: PathLike, dependencies: Sequence[PathLike]) -> bool:
    """Check if source files are newer than output."""

    if not os.path.isfile(output):
        return True

    output_mtime = os.path.getmtime(output)

    dep_mtime = 0.0
    for file in dependencies:
        mtime = os.path.getmtime(file)
        if mtime > dep_mtime:
            dep_mtime = mtime

    if dep_mtime > output_mtime:
        return True

    return False


def get_abs_paths(paths: Sequence[PathLike]) -> List[str]:
    """Return list of *paths* in absolute form."""

    paths_abs: List[str] = []
    for path in paths:
        if os.path.isabs(path):
            paths_abs.append(os.path.abspath(path))
        else:
            paths_abs.append(os.path.abspath(os.path.join(os.getcwd(), path)))

    return paths_abs


class Icarus(Simulator):
    @staticmethod
    def simulator_in_path() -> None:
        if shutil.which("iverilog") is None:
            raise SystemExit("ERROR: iverilog exacutable not found!")

    @staticmethod
    def check_toplevel_lang(toplevel_lang: Optional[str]) -> str:
        if toplevel_lang is None or toplevel_lang == "verilog":
            return "verilog"
        else:
            raise ValueError(
                f"iverilog does not support {toplevel_lang!r} as a toplevel_lang"
            )

    @staticmethod
    def get_include_options(includes: Sequence[str]) -> List[str]:
        return ["-I" + dir for dir in includes]

    @staticmethod
    def get_define_options(defines: Sequence[str]) -> List[str]:
        return ["-D" + define for define in defines]

    def get_parameter_options(self, parameters: Mapping[str, object]) -> List[str]:
        assert self.hdl_toplevel is not None
        return [
            f"-P{self.hdl_toplevel}.{name}={value}"
            for name, value in parameters.items()
        ]

    @property
    def sim_file(self) -> PathLike:
        return os.path.join(self.build_dir, "sim.vvp")

    def test_command(self) -> List[Command]:

        return [
            [
                "vvp",
                "-M",
                cocotb.config.libs_dir,
                "-m",
                cocotb.config.lib_name("vpi", "icarus"),
            ]
            + self.sim_args
            + [self.sim_file]
            + self.plus_args
        ]

    def build_command(self) -> List[Command]:

        if self.vhdl_sources:
            raise ValueError("This simulator does not support VHDL")

        cmd = []
        if outdated(self.sim_file, self.verilog_sources) or self.always:

            cmd = [
                ["iverilog", "-o", self.sim_file, "-D", "COCOTB_SIM=1", "-g2012"]
                + self.get_define_options(self.defines)
                + self.get_include_options(self.includes)
                + self.get_parameter_options(self.parameters)
                + self.compile_args
                + self.verilog_sources
            ]

        else:
            print("WARNING: Skipping compilation:" + self.sim_file)

        return cmd


class Questa(Simulator):
    @staticmethod
    def simulator_in_path() -> None:
        if shutil.which("vsim") is None:
            raise SystemExit("ERROR: vsim executable not found!")

    def check_toplevel_lang(self, toplevel_lang: Optional[str]) -> str:
        if toplevel_lang is None:
            if self.vhdl_sources and not self.verilog_sources:
                return "vhdl"
            elif self.verilog_sources and not self.vhdl_sources:
                return "verilog"
            else:
                raise ValueError("Must specify a toplevel_lang in a mixed design")
        elif toplevel_lang in ("verilog", "vhdl"):
            return toplevel_lang
        else:
            raise ValueError(
                f"Riviera does not support {toplevel_lang!r} as a toplevel_lang"
            )

    @staticmethod
    def get_include_options(includes: Sequence[str]) -> List[str]:
        return ["+incdir+" + as_tcl_value(dir) for dir in includes]

    @staticmethod
    def get_define_options(defines: Sequence[str]) -> List[str]:
        return ["+define+" + as_tcl_value(define) for define in defines]

    @staticmethod
    def get_parameter_options(parameters: Mapping[str, object]) -> List[str]:
        return ["-g" + name + "=" + str(value) for name, value in parameters.items()]

    def build_command(self) -> List[Command]:

        cmd = []

        if self.vhdl_sources:
            cmd.append(["vlib", as_tcl_value(self.library_name)])
            cmd.append(
                ["vcom", "-mixedsvvh"]
                + ["-work", as_tcl_value(self.library_name)]
                + [as_tcl_value(v) for v in self.compile_args]
                + [as_tcl_value(v) for v in self.vhdl_sources]
            )

        if self.verilog_sources:
            cmd.append(["vlib", as_tcl_value(self.library_name)])
            cmd.append(
                ["vlog", "-mixedsvvh"]
                + ([] if self.always else ["-incr"])
                + ["-work", as_tcl_value(self.library_name)]
                + ["+define+COCOTB_SIM"]
                + ["-sv"]
                + self.get_define_options(self.defines)
                + self.get_include_options(self.includes)
                + [as_tcl_value(v) for v in self.compile_args]
                + [as_tcl_value(v) for v in self.verilog_sources]
            )

        return cmd

    def test_command(self) -> List[Command]:

        cmd = []

        do_script = ""
        if self.waves:
            do_script += "log -recursive /*;"

        if not self.gui:
            do_script += "run -all; quit"

        fli_lib_path = cocotb.config.lib_name_path("fli", "questa")

        if self.toplevel_lang == "vhdl":

            if not os.path.isfile(fli_lib_path):
                raise SystemExit(
                    "ERROR: cocotb was not installed with an FLI library, as the mti.h header could not be located.\n\
                    If you installed an FLI-capable simulator after cocotb, you will need to reinstall cocotb.\n\
                    Please check the cocotb documentation on ModelSim support."
                )

            cmd.append(
                ["vsim"]
                + ["-gui" if self.gui else "-c"]
                + ["-onfinish", "stop" if self.gui else "exit"]
                + [
                    "-foreign",
                    "cocotb_init "
                    + as_tcl_value(cocotb.config.lib_name_path("fli", "questa")),
                ]
                + [as_tcl_value(v) for v in self.sim_args]
                + [as_tcl_value(v) for v in self.get_parameter_options(self.parameters)]
                + [as_tcl_value(self.sim_toplevel)]
                + ["-do", do_script]
            )

            self.env["GPI_EXTRA"] = (
                cocotb.config.lib_name_path("vpi", "questa") + ":cocotbvpi_entry_point"
            )

        else:
            cmd.append(
                ["vsim"]
                + ["-gui" if self.gui else "-c"]
                + ["-onfinish", "stop" if self.gui else "exit"]
                + ["-pli", as_tcl_value(cocotb.config.lib_name_path("vpi", "questa"))]
                + [as_tcl_value(v) for v in self.sim_args]
                + [as_tcl_value(v) for v in self.get_parameter_options(self.parameters)]
                + [as_tcl_value(self.sim_toplevel)]
                + [as_tcl_value(v) for v in self.plus_args]
                + ["-do", do_script]
            )

            if os.path.isfile(fli_lib_path):
                self.env["GPI_EXTRA"] = (
                    cocotb.config.lib_name_path("fli", "questa")
                    + ":cocotbfli_entry_point"
                )
            else:
                print(
                    "WARNING: FLI library not found. Mixed-mode simulation will not be available."
                )

        return cmd


class Ghdl(Simulator):
    @staticmethod
    def simulator_in_path() -> None:
        if shutil.which("ghdl") is None:
            raise SystemExit("ERROR: ghdl executable not found!")

    def check_toplevel_lang(self, toplevel_lang: Optional[str]) -> str:
        if toplevel_lang is None or toplevel_lang == "vhdl":
            return "vhdl"
        else:
            raise ValueError(
                f"GHDL does not support {toplevel_lang!r} as a toplevel_lang"
            )

    @staticmethod
    def get_include_options(includes: Sequence[str]) -> List[str]:
        return [f"-I{dir}" for dir in includes]

    @staticmethod
    def get_define_options(defines: Sequence[str]) -> List[str]:
        return [f"-D{define}" for define in defines]

    @staticmethod
    def get_parameter_options(parameters: Mapping[str, object]) -> List[str]:
        return ["-g" + name + "=" + str(value) for name, value in parameters.items()]

    def build_command(self) -> List[Command]:

        if self.verilog_sources:
            raise ValueError("This simulator does not support Verilog")

        if self.hdl_toplevel is None:
            raise ValueError(
                "This simulator requires the hdl_toplevel parameter to be specified"
            )

        cmd = [
            ["ghdl", "-i"]
            + [f"--work={self.library_name}"]
            + self.compile_args
            + [source_file]
            for source_file in self.vhdl_sources
        ]

        cmd += [
            ["ghdl", "-m"]
            + [f"--work={self.library_name}"]
            + self.compile_args
            + [self.hdl_toplevel]
        ]

        return cmd

    def test_command(self) -> List[Command]:

        cmd = [
            ["ghdl", "-r"]
            + [self.sim_toplevel]
            + ["--vpi=" + cocotb.config.lib_name_path("vpi", "ghdl")]
            + self.sim_args
            + self.get_parameter_options(self.parameters)
        ]

        return cmd


class Riviera(Simulator):
    @staticmethod
    def simulator_in_path() -> None:
        if shutil.which("vsimsa") is None:
            raise SystemExit("ERROR: vsimsa executable not found!")

    def check_toplevel_lang(self, toplevel_lang: Optional[str]) -> str:
        if toplevel_lang is None:
            if self.vhdl_sources and not self.verilog_sources:
                return "vhdl"
            elif self.verilog_sources and not self.vhdl_sources:
                return "verilog"
            else:
                raise ValueError(
                    "Must specify a toplevel_lang in a mixed-language design"
                )
        elif toplevel_lang in ("verilog", "vhdl"):
            return toplevel_lang
        else:
            raise ValueError(
                f"Riviera does not support {toplevel_lang!r} as a toplevel_lang"
            )

    @staticmethod
    def get_include_options(includes: Sequence[str]) -> List[str]:
        return ["+incdir+" + as_tcl_value(dir) for dir in includes]

    @staticmethod
    def get_define_options(defines: Sequence[str]) -> List[str]:
        return ["+define+" + as_tcl_value(define) for define in defines]

    @staticmethod
    def get_parameter_options(parameters: Mapping[str, object]) -> List[str]:
        return ["-g" + name + "=" + str(value) for name, value in parameters.items()]

    def build_command(self) -> List[Command]:

        do_script = "\nonerror {\n quit -code 1 \n} \n"

        out_file = os.path.join(
            self.build_dir, self.library_name, self.library_name + ".lib"
        )

        if outdated(out_file, self.verilog_sources + self.vhdl_sources) or self.always:

            do_script += "alib {RTL_LIBRARY} \n".format(
                RTL_LIBRARY=as_tcl_value(self.library_name)
            )

            if self.vhdl_sources:
                do_script += (
                    "acom -work {RTL_LIBRARY} {EXTRA_ARGS} {VHDL_SOURCES}\n".format(
                        RTL_LIBRARY=as_tcl_value(self.library_name),
                        VHDL_SOURCES=" ".join(
                            as_tcl_value(v) for v in self.vhdl_sources
                        ),
                        EXTRA_ARGS=" ".join(as_tcl_value(v) for v in self.compile_args),
                    )
                )

            if self.verilog_sources:
                do_script += "alog -work {RTL_LIBRARY} +define+COCOTB_SIM -sv {DEFINES} {INCDIR} {EXTRA_ARGS} {VERILOG_SOURCES} \n".format(
                    RTL_LIBRARY=as_tcl_value(self.library_name),
                    VERILOG_SOURCES=" ".join(
                        as_tcl_value(v) for v in self.verilog_sources
                    ),
                    DEFINES=" ".join(self.get_define_options(self.defines)),
                    INCDIR=" ".join(self.get_include_options(self.includes)),
                    EXTRA_ARGS=" ".join(as_tcl_value(v) for v in self.compile_args),
                )
        else:
            print("WARNING: Skipping compilation:" + out_file)

        do_file = tempfile.NamedTemporaryFile(delete=False)
        do_file.write(do_script.encode())
        do_file.close()

        return [["vsimsa"] + ["-do"] + ["do"] + [do_file.name]]

    def test_command(self) -> List[Command]:

        do_script = "\nonerror {\n quit -code 1 \n} \n"

        if self.toplevel_lang == "vhdl":
            do_script += "asim +access +w -interceptcoutput -O2 -loadvhpi {EXT_NAME} {EXTRA_ARGS} {TOPLEVEL} \n".format(
                TOPLEVEL=as_tcl_value(self.sim_toplevel),
                EXT_NAME=as_tcl_value(cocotb.config.lib_name_path("vhpi", "riviera")),
                EXTRA_ARGS=" ".join(
                    as_tcl_value(v)
                    for v in (
                        self.sim_args + self.get_parameter_options(self.parameters)
                    )
                ),
            )

            self.env["GPI_EXTRA"] = (
                cocotb.config.lib_name_path("vpi", "riviera") + ":cocotbvpi_entry_point"
            )
        else:
            do_script += "asim +access +w -interceptcoutput -O2 -pli {EXT_NAME} {EXTRA_ARGS} {TOPLEVEL} {PLUS_ARGS} \n".format(
                TOPLEVEL=as_tcl_value(self.sim_toplevel),
                EXT_NAME=as_tcl_value(cocotb.config.lib_name_path("vpi", "riviera")),
                EXTRA_ARGS=" ".join(
                    as_tcl_value(v)
                    for v in (
                        self.sim_args + self.get_parameter_options(self.parameters)
                    )
                ),
                PLUS_ARGS=" ".join(as_tcl_value(v) for v in self.plus_args),
            )

            self.env["GPI_EXTRA"] = (
                cocotb.config.lib_name_path("vhpi", "riviera")
                + ":cocotbvhpi_entry_point"
            )

        if self.waves:
            do_script += "log -recursive /*;"

        do_script += "run -all \nexit"

        do_file = tempfile.NamedTemporaryFile(delete=False)
        do_file.write(do_script.encode())
        do_file.close()

        return [["vsimsa"] + ["-do"] + ["do"] + [do_file.name]]


class Verilator(Simulator):
    def simulator_in_path(self) -> None:
        executable = shutil.which("verilator")
        if executable is None:
            raise SystemExit("ERROR: verilator executable not found!")
        self.executable = executable

    @staticmethod
    def check_toplevel_lang(toplevel_lang: Optional[str]) -> str:
        if toplevel_lang is None or toplevel_lang == "verilog":
            return "verilog"
        else:
            raise ValueError(
                f"Verilator does not support {toplevel_lang!r} as a toplevel_lang"
            )

    @staticmethod
    def get_include_options(includes: Sequence[str]) -> List[str]:
        return ["-I" + dir for dir in includes]

    @staticmethod
    def get_define_options(defines: Sequence[str]) -> List[str]:
        return ["-D" + define for define in defines]

    @staticmethod
    def get_parameter_options(parameters: Mapping[str, object]) -> List[str]:
        return ["-G" + name + "=" + str(value) for name, value in parameters.items()]

    def build_command(self) -> List[Command]:

        if self.vhdl_sources:
            raise ValueError("This simulator does not support VHDL")

        if self.hdl_toplevel is None:
            raise ValueError(
                "This simulator requires hdl_toplevel parameter to be specified"
            )

        cmd = []

        verilator_cpp = os.path.join(
            os.path.dirname(cocotb.__file__),
            "share",
            "lib",
            "verilator",
            "verilator.cpp",
        )

        cmd.append(
            [
                "perl",
                self.executable,
                "-cc",
                "--exe",
                "-Mdir",
                self.build_dir,
                "-DCOCOTB_SIM=1",
                "--top-module",
                self.hdl_toplevel,
                "--vpi",
                "--public-flat-rw",
                "--prefix",
                "Vtop",
                "-o",
                self.hdl_toplevel,
                "-LDFLAGS",
                "-Wl,-rpath,{LIB_DIR} -L{LIB_DIR} -lcocotbvpi_verilator".format(
                    LIB_DIR=cocotb.config.libs_dir
                ),
            ]
            + self.compile_args
            + self.get_define_options(self.defines)
            + self.get_include_options(self.includes)
            + self.get_parameter_options(self.parameters)
            + [verilator_cpp]
            + self.verilog_sources
        )

        cmd.append(["make", "-C", self.build_dir, "-f", "Vtop.mk"])

        return cmd

    def test_command(self) -> List[Command]:
        out_file = os.path.join(self.build_dir, self.sim_toplevel)
        return [[out_file] + self.plus_args]


def get_runner(simulator_name: str) -> Type[Simulator]:

    sim_name = simulator_name.lower()
    supported_sims: Dict[str, Type[Simulator]] = {
        "icarus": Icarus,
        "questa": Questa,
        "ghdl": Ghdl,
        "riviera": Riviera,
        "verilator": Verilator,
    }  # TODO: "ius", "xcelium", "vcs"
    try:
        return supported_sims[sim_name]
    except KeyError:
        raise NotImplementedError(
            "Set SIM variable. Supported: " + ", ".join(supported_sims)
        ) from None


def clean(recursive: bool = False) -> None:
    dir = os.getcwd()

    def rm_clean() -> None:
        build_dir = os.path.join(dir, "sim_build")
        if os.path.isdir(build_dir):
            print("INFO: Removing:", build_dir)
            shutil.rmtree(build_dir, ignore_errors=True)

    rm_clean()

    if recursive:
        for dir, _, _ in os.walk(dir):
            rm_clean()
