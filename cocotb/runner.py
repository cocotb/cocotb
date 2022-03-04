# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Build HDL and run cocotb tests."""

import abc
import os
import re
import shutil
import subprocess
import sys
import tempfile
import warnings
from contextlib import suppress
from pathlib import Path, PurePath
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

        self.supported_languages: Sequence[str] = ()
        self.simulator_in_path()

        self.env: Dict[str, str] = {}

        # for running test() independently of build()
        self.build_dir: Path = Path("sim_build")
        self.parameters: Mapping[str, object] = {}

    @abc.abstractmethod
    def simulator_in_path(self) -> None:
        """Raise exception if the simulator executable does not exist in :envvar:`PATH`.

        Raises:
            SystemExit: Simulator executable does not exist in :envvar:`PATH`.
        """

        raise NotImplementedError()

    def check_toplevel_lang(self, toplevel_lang: Optional[str]) -> str:
        """Return *toplevel_lang* if supported by simulator, raise exception otherwise.

        Returns:
            *toplevel_lang* if supported by the simulator.

        Raises:
            ValueError: *toplevel_lang* is not supported by the simulator.
        """
        if toplevel_lang is None:
            if self.vhdl_sources and not self.verilog_sources:
                res = "vhdl"
            elif self.verilog_sources and not self.vhdl_sources:
                res = "verilog"
            else:
                raise ValueError(
                    "{type(self).__qualname__}: Must specify a toplevel_lang in a mixed-language design"
                )
        else:
            res = toplevel_lang

        if res in self.supported_languages:
            return res
        else:
            raise ValueError(
                f"{type(self).__qualname__}: toplevel_lang={toplevel_lang!r} is not "
                f"in supported list: {self.supported_languages}"
            )

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
        verilog_sources: Sequence[str] = [],
        vhdl_sources: Sequence[str] = [],
        includes: Sequence[Path] = [],
        defines: Sequence[str] = [],
        parameters: Mapping[str, object] = {},
        extra_args: Sequence[str] = [],
        toplevel: Optional[str] = None,
        always: bool = False,
        build_dir: PathLike = "sim_build",
    ) -> None:
        """Build the HDL sources.

        Args:
            library_name: The library name to compile into.
            verilog_sources: Verilog source files.
            vhdl_sources: VHDL source files.
            includes: Verilog include directories.
            defines: Defines to set.
            parameters: Verilog parameters or VHDL generics.
            extra_args: Extra arguments for the simulator.
            toplevel: The name of the HDL toplevel module.
            always: Always run the build step if set.
            build_dir: Directory to run the build step in.
        """

        self.build_dir = Path(build_dir).resolve()
        os.makedirs(self.build_dir, exist_ok=True)

        # note: to avoid mutating argument defaults, we ensure that no value
        # is written without a copy. This is much more concise and leads to
        # a better docstring than using `None` as a default in the parameters
        # list.
        self.library_name = library_name
        self.verilog_sources: List[str] = get_abs_paths(verilog_sources)
        self.vhdl_sources: List[str] = get_abs_paths(vhdl_sources)
        self.includes: List[str] = get_abs_paths(includes)
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
        """Run the tests.

        Args:
            py_module: Name(s) of the Python module(s) containing the tests to run.
            toplevel: Name of the HDL toplevel module.
            toplevel_lang: Language of the HDL toplevel module.
            testcase: Name of a specific testcase to run.
                If not set, run all testcases found in *py_module*.
            seed: A specific random seed to use.
            python_search: Path to search extra Python modules in.
            extra_args: Extra arguments for the simulator.
            plus_args: 'plusargs' to set for the simulator.
            extra_env: Extra environment variables to set.
            waves: Record signal traces.
                Overrides the environment variable :envvar:`COCOTB_WAVES` if set.
            gui: Run with simulator GUI.
                Overrides the environment variable :envvar:`COCOTB_GUI` if set.
            parameters: Verilog parameters or VHDL generics.
            build_dir: Directory the build step has been run in.
            sim_dir: Directory to run the simulation in.

        Returns:
            The absolute location of the results file which can be
            defined by the environment variable :envvar:`COCOTB_RESULTS_FILE`.
            The default is :file:`{build_dir}/{pytest_test_name}.results.xml`
            when run with ``pytest``,
            :file:`{build_dir}/results.xml` otherwise.
        """

        __tracebackhide__ = True  # Hide the traceback when using pytest

        if build_dir is not None:
            self.build_dir = Path(build_dir)

        if parameters is not None:
            self.parameters = dict(parameters)

        if sim_dir is None:
            self.sim_dir = self.build_dir
        else:
            self.sim_dir = Path(sim_dir).resolve()

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
        pytest_current_test = os.getenv("PYTEST_CURRENT_TEST", "")
        if pytest_current_test:
            self.current_test_name = pytest_current_test.split(":")[-1].split(" ")[0]
            results_xml_name = f"{self.current_test_name}.results.xml"
        else:
            self.current_test_name = "test"
            results_xml_name = "results.xml"

        results_xml_file = os.getenv(
            "COCOTB_RESULTS_FILE", str(Path(self.build_dir) / results_xml_name)
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
        """Return simulator-specific formatted option strings with *includes* directories."""

        raise NotImplementedError()

    @abc.abstractmethod
    def get_define_options(self, defines: Sequence[str]) -> List[str]:
        """Return simulator-specific formatted option strings with *defines* macros."""

        raise NotImplementedError()

    @abc.abstractmethod
    def get_parameter_options(self, parameters: Mapping[str, object]) -> List[str]:
        """Return simulator-specific formatted option strings with *parameters*/generics."""

        raise NotImplementedError()

    def execute(self, cmds: Sequence[Command], cwd: PathLike) -> None:

        __tracebackhide__ = True  # Hide the traceback when using PyTest.

        for cmd in cmds:
            print(f"INFO: Running command {' '.join(cmd)} in directory {cwd}")

            # TODO: create a thread to handle stderr and log as error?
            # TODO: log forwarding

            process = subprocess.run(cmd, cwd=cwd, env=self.env)

            if process.returncode != 0:
                raise SystemExit(
                    f"Process {process.args[0]!r} terminated with error {process.returncode}"
                )


def check_results_file(results_xml_file: PathLike) -> None:
    """Raise exception if *results_xml_file* does not exist or contains failed tests.

    Raises:
        SystemExit: *results_xml_file* is non-existent or contains fails.
    """

    __tracebackhide__ = True  # Hide the traceback when using PyTest.

    results_file_exist = Path(results_xml_file).is_file()
    if not results_file_exist:
        raise SystemExit(
            "ERROR: Simulation terminated abnormally. Results file not found."
        )

    num_tests = 0
    num_failed = 0

    tree = ET.parse(results_xml_file)
    for ts in tree.iter("testsuite"):
        for tc in ts.iter("testcase"):
            num_tests += 1
            for _ in tc.iter("failure"):
                num_failed += 1

    if num_failed:
        raise SystemExit(f"ERROR: Failed {num_failed} of {num_tests} tests.")


def outdated(output: PathLike, dependencies: Sequence[PathLike]) -> bool:
    """Return ``True`` if any source files in *dependencies* are newer than the *output* directory.

    Returns:
        ``True`` if any source files are newer, ``False`` otherwise.
    """

    if not Path(output).is_file():
        return True

    output_mtime = Path(output).stat().st_mtime

    dep_mtime = 0.0
    for dependency in dependencies:
        mtime = Path(dependency).stat().st_mtime
        if mtime > dep_mtime:
            dep_mtime = mtime

    if dep_mtime > output_mtime:
        return True

    return False


def get_abs_paths(paths: Sequence[PathLike]) -> List[str]:
    """Return list of *paths* in absolute form."""

    paths_abs: List[str] = []
    for path in paths:
        if PurePath(path).is_absolute():
            paths_abs.append(str(Path(path).resolve()))
        else:
            paths_abs.append(str((Path(os.getcwd()) / path).resolve()))

    return paths_abs


class Icarus(Simulator):
    def __init__(self) -> None:
        super().__init__()
        self.supported_languages = ("verilog",)

    @staticmethod
    def simulator_in_path() -> None:
        if shutil.which("iverilog") is None:
            raise SystemExit("ERROR: iverilog executable not found!")

    @staticmethod
    def get_include_options(includes: Sequence[str]) -> List[str]:
        return ["-I" + include for include in includes]

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
    def sim_file(self) -> Path:
        return Path(self.build_dir) / "sim.vvp"

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
            + [str(self.sim_file)]
            + self.plus_args
        ]

    def build_command(self) -> List[Command]:

        if self.vhdl_sources:
            raise ValueError("This simulator does not support VHDL")

        cmds = []
        if outdated(self.sim_file, self.verilog_sources) or self.always:

            cmds = [
                ["iverilog", "-o", str(self.sim_file), "-D", "COCOTB_SIM=1", "-g2012"]
                + self.get_define_options(self.defines)
                + self.get_include_options(self.includes)
                + self.get_parameter_options(self.parameters)
                + self.compile_args
                + self.verilog_sources
            ]

        else:
            print("WARNING: Skipping compilation of", self.sim_file)

        return cmds


class Questa(Simulator):
    def __init__(self) -> None:
        super().__init__()
        self.supported_languages = ("verilog", "vhdl")

    @staticmethod
    def simulator_in_path() -> None:
        if shutil.which("vsim") is None:
            raise SystemExit("ERROR: vsim executable not found!")

    @staticmethod
    def get_include_options(includes: Sequence[str]) -> List[str]:
        return ["+incdir+" + as_tcl_value(include) for include in includes]

    @staticmethod
    def get_define_options(defines: Sequence[str]) -> List[str]:
        return ["+define+" + as_tcl_value(define) for define in defines]

    @staticmethod
    def get_parameter_options(parameters: Mapping[str, object]) -> List[str]:
        return ["-g" + name + "=" + str(value) for name, value in parameters.items()]

    def build_command(self) -> List[Command]:

        cmds = []

        if self.vhdl_sources:
            cmds.append(["vlib", as_tcl_value(self.library_name)])
            cmds.append(
                ["vcom", "-mixedsvvh"]
                + ["-work", as_tcl_value(self.library_name)]
                + [as_tcl_value(v) for v in self.compile_args]
                + [as_tcl_value(v) for v in self.vhdl_sources]
            )

        if self.verilog_sources:
            cmds.append(["vlib", as_tcl_value(self.library_name)])
            cmds.append(
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

        return cmds

    def test_command(self) -> List[Command]:

        cmds = []

        do_script = ""
        if self.waves:
            do_script += "log -recursive /*;"

        if not self.gui:
            do_script += "run -all; quit"

        fli_lib_path = cocotb.config.lib_name_path("fli", "questa")

        if self.toplevel_lang == "vhdl":

            if not Path(fli_lib_path).is_file():
                raise SystemExit(
                    "ERROR: cocotb was not installed with an FLI library, as the mti.h header could not be located.\n\
                    If you installed an FLI-capable simulator after cocotb, you will need to reinstall cocotb.\n\
                    Please check the cocotb documentation on ModelSim support."
                )

            cmds.append(
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
            cmds.append(
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

            if Path(fli_lib_path).is_file():
                self.env["GPI_EXTRA"] = (
                    cocotb.config.lib_name_path("fli", "questa")
                    + ":cocotbfli_entry_point"
                )
            else:
                print(
                    "WARNING: FLI library not found. Mixed-mode simulation will not be available."
                )

        return cmds


class Ghdl(Simulator):
    def __init__(self) -> None:
        super().__init__()
        self.supported_languages = "vhdl"

    @staticmethod
    def simulator_in_path() -> None:
        if shutil.which("ghdl") is None:
            raise SystemExit("ERROR: ghdl executable not found!")

    @staticmethod
    def get_include_options(includes: Sequence[str]) -> List[str]:
        return [f"-I{include}" for include in includes]

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

        cmds = [
            ["ghdl", "-i"]
            + [f"--work={self.library_name}"]
            + self.compile_args
            + [source_file]
            for source_file in self.vhdl_sources
        ]

        cmds += [
            ["ghdl", "-m"]
            + [f"--work={self.library_name}"]
            + self.compile_args
            + [self.hdl_toplevel]
        ]

        return cmds

    def test_command(self) -> List[Command]:

        cmds = [
            ["ghdl", "-r"]
            + [self.sim_toplevel]
            + ["--vpi=" + cocotb.config.lib_name_path("vpi", "ghdl")]
            + self.sim_args
            + self.get_parameter_options(self.parameters)
        ]

        return cmds


class Riviera(Simulator):
    def __init__(self) -> None:
        super().__init__()
        self.supported_languages = ("verilog", "vhdl")

    @staticmethod
    def simulator_in_path() -> None:
        if shutil.which("vsimsa") is None:
            raise SystemExit("ERROR: vsimsa executable not found!")

    @staticmethod
    def get_include_options(includes: Sequence[str]) -> List[str]:
        return ["+incdir+" + as_tcl_value(include) for include in includes]

    @staticmethod
    def get_define_options(defines: Sequence[str]) -> List[str]:
        return ["+define+" + as_tcl_value(define) for define in defines]

    @staticmethod
    def get_parameter_options(parameters: Mapping[str, object]) -> List[str]:
        return ["-g" + name + "=" + str(value) for name, value in parameters.items()]

    def build_command(self) -> List[Command]:

        do_script = "\nonerror {\n quit -code 1 \n} \n"

        out_file = self.build_dir / self.library_name / (self.library_name + ".lib")

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
            print("WARNING: Skipping compilation of", out_file)

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
    def __init__(self) -> None:
        super().__init__()
        self.supported_languages = ("verilog",)

    def simulator_in_path(self) -> None:
        executable = shutil.which("verilator")
        if executable is None:
            raise SystemExit("ERROR: verilator executable not found!")
        self.executable = executable

    @staticmethod
    def get_include_options(includes: Sequence[str]) -> List[str]:
        return ["-I" + include for include in includes]

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

        verilator_cpp = (
            PurePath(cocotb.__file__).parent
            / "share"
            / "lib"
            / "verilator"
            / "verilator.cpp"
        )

        cmds = []
        cmds += [
            ["perl"]
            + [self.executable]
            + ["-cc"]
            + ["--exe"]
            + ["-Mdir", str(self.build_dir)]
            + ["-DCOCOTB_SIM=1"]
            + ["--top-module", self.hdl_toplevel]
            + ["--vpi"]
            + ["--public-flat-rw"]
            + ["--prefix"]
            + ["Vtop"]
            + ["-o", self.hdl_toplevel]
            + [
                "-LDFLAGS",
                "-Wl,-rpath,{LIB_DIR} -L{LIB_DIR} -lcocotbvpi_verilator".format(
                    LIB_DIR=cocotb.config.libs_dir
                ),
            ]
            + self.compile_args
            + self.get_define_options(self.defines)
            + self.get_include_options(self.includes)
            + self.get_parameter_options(self.parameters)
            + [str(verilator_cpp)]
            + self.verilog_sources
        ]

        cmds += [
            ["make"] + ["--directory", str(self.build_dir)] + ["--file", "Vtop.mk"]
        ]

        return cmds

    def test_command(self) -> List[Command]:
        out_file = self.build_dir / self.sim_toplevel
        return [[str(out_file)] + self.plus_args]


class Xcelium(Simulator):
    def __init__(self) -> None:
        super().__init__()
        self.supported_languages = ("verilog", "vhdl")

    @staticmethod
    def simulator_in_path() -> None:
        if shutil.which("xrun") is None:
            raise SystemExit("ERROR: xrun executable not found!")

    @staticmethod
    def get_include_options(includes: Sequence[str]) -> List[str]:
        return [f"-incdir {include}" for include in includes]

    @staticmethod
    def get_define_options(defines: Sequence[str]) -> List[str]:
        return [f"-define {define}" for define in defines]

    @staticmethod
    def get_parameter_options(parameters: Mapping[str, object]) -> List[str]:
        return [f'-gpg "{name} => {value}"' for name, value in parameters.items()]

    def build_command(self) -> List[Command]:

        self.env["CDS_AUTO_64BIT"] = "all"
        cmds = [
            ["xrun"]
            + ["-logfile xrun_build.log"]
            + ["-elaborate"]
            + [f"-xmlibdirname {self.build_dir}/xrun_snapshot"]
            + ["-licqueue"]
            # TODO: way to switch to these verbose messages?:
            + ["-messages"]
            + ["-gverbose"]  # print assigned generics/parameters
            + ["-plinowarn"]
            # + ["-pliverbose"]
            # + ["-plidebug"]  # Enhance the profile output with PLI info
            # + ["-plierr_verbose"]  # Expand handle info in PLI/VPI/VHPI messages
            # + ["-vpicompat 1800v2005"]  # <1364v1995|1364v2001|1364v2005|1800v2005> Specify the IEEE VPI
            + ["-access +rwc"]
            + [
                "-loadvpi "
                + cocotb.config.lib_name_path("vpi", "xcelium")
                + ":vlog_startup_routines_bootstrap"
            ]
            + [f"-work {self.library_name}"]
            + self.compile_args
            + ["-define COCOTB_SIM"]
            + self.get_define_options(self.defines)
            + self.get_include_options(self.includes)
            + self.get_parameter_options(self.parameters)
            + [f"-top {self.hdl_toplevel}"]
            + self.vhdl_sources
            + self.verilog_sources
        ]

        return cmds

    def test_command(self) -> List[Command]:
        self.env["CDS_AUTO_64BIT"] = "all"

        tmpdir = f"implicit_tmpdir_{self.current_test_name}"
        cmds = [["mkdir", "-p", tmpdir]]

        cmds += [
            ["xrun"]
            + [f"-logfile xrun_{self.current_test_name}.log"]
            + [
                f"-xmlibdirname {self.build_dir}/xrun_snapshot -cds_implicit_tmpdir {tmpdir}"
            ]
            + ["-licqueue"]
            # TODO: way to switch to these verbose messages?:
            + ["-messages"]
            + ["-plinowarn"]
            # + ["-pliverbose"]
            # + ["-plidebug"]  # Enhance the profile output with PLI info
            # + ["-plierr_verbose"]  # Expand handle info in PLI/VPI/VHPI messages
            # + ["-vpicompat 1800v2005"]  # <1364v1995|1364v2001|1364v2005|1800v2005> Specify the IEEE VPI
            + ["-R"]
            + self.sim_args
            + self.plus_args
            + ["-gui" if self.gui else ""]
            + [
                '-input "@probe -create {self.sim_toplevel} -all -depth all"'
                if self.waves
                else ""
            ]
        ]
        self.env["GPI_EXTRA"] = (
            cocotb.config.lib_name_path("vhpi", "xcelium") + ":cocotbvhpi_entry_point"
        )

        return cmds


def get_runner(simulator_name: str) -> Type[Simulator]:

    sim_name = simulator_name.lower()
    supported_sims: Dict[str, Type[Simulator]] = {
        "icarus": Icarus,
        "questa": Questa,
        "ghdl": Ghdl,
        "riviera": Riviera,
        "verilator": Verilator,
        "xcelium": Xcelium,
        # TODO: "vcs": Vcs,
        # TODO: "activehdl": ActiveHdl,
    }
    try:
        return supported_sims[sim_name]
    except KeyError:
        raise NotImplementedError(
            "Set SIM variable. Supported: " + ", ".join(supported_sims)
        ) from None


def clean(recursive: bool = False) -> None:
    dir = os.getcwd()

    def rm_clean() -> None:
        build_dir = Path(dir) / "sim_build"
        if Path(build_dir).is_dir():
            print("INFO: Removing", build_dir)
            shutil.rmtree(build_dir, ignore_errors=True)

    rm_clean()

    if recursive:
        for dir, _, _ in os.walk(dir):
            rm_clean()
