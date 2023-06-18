# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Build HDL and run cocotb tests."""

# TODO: maybe do globbing and expanduser/expandvars in --include, --vhdl-sources, --verilog-sources
# TODO: create a short README and a .gitignore (content: "*") in both build_dir and test_dir? (Some other tools do this.)
# TODO: support timescale
# TODO: support custom dependencies

import abc
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import warnings
from contextlib import suppress
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple, Type, Union
from xml.etree import cElementTree as ET

import find_libpython

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


def shlex_join(split_command):
    """
    Return a shell-escaped string from *split_command*
    This is here more for compatibility purposes
    """
    return " ".join(shlex.quote(arg) for arg in split_command)


class Simulator(abc.ABC):

    supported_gpi_interfaces: Dict[str, List[str]] = {}

    def __init__(self) -> None:

        self._simulator_in_path()

        self.env: Dict[str, str] = {}

        # for running test() independently of build()
        self.build_dir: Path = get_abs_path("sim_build")
        self.parameters: Mapping[str, object] = {}

    @abc.abstractmethod
    def _simulator_in_path(self) -> None:
        """Raise exception if the simulator executable does not exist in :envvar:`PATH`.

        Raises:
            SystemExit: Simulator executable does not exist in :envvar:`PATH`.
        """

        raise NotImplementedError()

    def _check_hdl_toplevel_lang(self, hdl_toplevel_lang: Optional[str]) -> str:
        """Return *hdl_toplevel_lang* if supported by simulator, raise exception otherwise.

        Returns:
            *hdl_toplevel_lang* if supported by the simulator.

        Raises:
            ValueError: *hdl_toplevel_lang* is not supported by the simulator.
        """
        if hdl_toplevel_lang is None:
            if self.vhdl_sources and not self.verilog_sources:
                lang = "vhdl"
            elif self.verilog_sources and not self.vhdl_sources:
                lang = "verilog"
            else:
                raise ValueError(
                    f"{type(self).__qualname__}: Must specify a hdl_toplevel_lang in a mixed-language design"
                )
        else:
            lang = hdl_toplevel_lang

        if lang in self.supported_gpi_interfaces.keys():
            return lang
        else:
            raise ValueError(
                f"{type(self).__qualname__}: hdl_toplevel_lang {hdl_toplevel_lang!r} is not "
                f"in supported list: {', '.join(self.supported_gpi_interfaces.keys())}"
            )

    def _set_env(self) -> None:
        """Set environment variables for sub-processes."""

        for e in os.environ:
            self.env[e] = os.environ[e]

        if "LIBPYTHON_LOC" not in self.env:
            self.env["LIBPYTHON_LOC"] = find_libpython.find_libpython()

        self.env["PATH"] += os.pathsep + cocotb.config.libs_dir
        self.env["PYTHONPATH"] = os.pathsep.join(sys.path)
        self.env["PYTHONHOME"] = sys.prefix
        self.env["TOPLEVEL"] = self.sim_hdl_toplevel
        self.env["MODULE"] = self.test_module

    @abc.abstractmethod
    def _build_command(self) -> Sequence[Command]:
        """Return command to build the HDL sources."""

        raise NotImplementedError()

    @abc.abstractmethod
    def _test_command(self) -> Sequence[Command]:
        """Return command to run a test."""

        raise NotImplementedError()

    def build(
        self,
        hdl_library: str = "top",
        verilog_sources: Sequence[PathLike] = [],
        vhdl_sources: Sequence[PathLike] = [],
        includes: Sequence[PathLike] = [],
        defines: Mapping[str, object] = {},
        parameters: Mapping[str, object] = {},
        build_args: Sequence[str] = [],
        hdl_toplevel: Optional[str] = None,
        always: bool = False,
        build_dir: PathLike = "sim_build",
        verbose: bool = False,
    ) -> None:
        """Build the HDL sources.

        Args:
            hdl_library: The library name to compile into.
            verilog_sources: Verilog source files to build.
            vhdl_sources: VHDL source files to build.
            includes: Verilog include directories.
            defines: Defines to set.
            parameters: Verilog parameters or VHDL generics.
            build_args: Extra build arguments for the simulator.
            hdl_toplevel: The name of the HDL toplevel module.
            always: Always run the build step.
            build_dir: Directory to run the build step in.
            verbose: Enable verbose messages.
        """

        self.build_dir = get_abs_path(build_dir)
        os.makedirs(self.build_dir, exist_ok=True)

        # note: to avoid mutating argument defaults, we ensure that no value
        # is written without a copy. This is much more concise and leads to
        # a better docstring than using `None` as a default in the parameters
        # list.
        self.hdl_library: str = hdl_library
        self.verilog_sources: List[Path] = get_abs_paths(verilog_sources)
        self.vhdl_sources: List[Path] = get_abs_paths(vhdl_sources)
        self.includes: List[Path] = get_abs_paths(includes)
        self.defines = dict(defines)
        self.parameters = dict(parameters)
        self.build_args = list(build_args)
        self.always: bool = always
        self.hdl_toplevel: Optional[str] = hdl_toplevel
        self.verbose: bool = verbose

        for e in os.environ:
            self.env[e] = os.environ[e]

        cmds: Sequence[Command] = self._build_command()
        self._execute(cmds, cwd=self.build_dir)

    def test(
        self,
        test_module: Union[str, Sequence[str]],
        hdl_toplevel: str,
        hdl_toplevel_library: str = "top",
        hdl_toplevel_lang: Optional[str] = None,
        gpi_interfaces: Optional[List[str]] = None,
        testcase: Optional[Union[str, Sequence[str]]] = None,
        seed: Optional[Union[str, int]] = None,
        test_args: Sequence[str] = [],
        plusargs: Sequence[str] = [],
        extra_env: Mapping[str, str] = {},
        waves: Optional[bool] = None,
        gui: Optional[bool] = None,
        parameters: Mapping[str, object] = None,
        build_dir: Optional[PathLike] = None,
        test_dir: Optional[PathLike] = None,
        results_xml: str = "results.xml",
        verbose: bool = False,
    ) -> Path:
        """Run the tests.

        Args:
            test_module: Name(s) of the Python module(s) containing the tests to run.
                Can be a comma-separated list.
            hdl_toplevel: Name of the HDL toplevel module.
            hdl_toplevel_library: The library name for HDL toplevel module.
            hdl_toplevel_lang: Language of the HDL toplevel module.
            gpi_interfaces: List of GPI interfaces to use, with the first one being the entry point.
            testcase: Name(s) of a specific testcase(s) to run.
                If not set, run all testcases found in *test_module*.
                Can be a comma-separated list.
            seed: A specific random seed to use.
            test_args: Extra arguments for the simulator.
            plusargs: 'plusargs' to set for the simulator.
            extra_env: Extra environment variables to set.
            waves: Record signal traces.
            gui: Run with simulator GUI.
            parameters: Verilog parameters or VHDL generics.
            build_dir: Directory the build step has been run in.
            test_dir: Directory to run the tests in.
            results_xml: Name of xUnit XML file to store test results in.
                When running with pytest, the testcase name is prefixed to this name.
            verbose: Enable verbose messages.

        Returns:
            The absolute location of the results XML file which can be
            defined by the *results_xml* argument.
            The default is :file:`{build_dir}/{pytest_test_name}.results.xml`
            when run with ``pytest``,
            :file:`{build_dir}/results.xml` otherwise.
        """

        __tracebackhide__ = True  # Hide the traceback when using pytest

        if build_dir is not None:
            self.build_dir = get_abs_path(build_dir)

        if parameters is not None:
            self.parameters = dict(parameters)

        if test_dir is None:
            self.test_dir = self.build_dir
        else:
            self.test_dir = get_abs_path(test_dir)
        os.makedirs(self.test_dir, exist_ok=True)

        if isinstance(test_module, str):
            self.test_module = test_module
        else:
            self.test_module = ",".join(test_module)

        # note: to avoid mutating argument defaults, we ensure that no value
        # is written without a copy. This is much more concise and leads to
        # a better docstring than using `None` as a default in the parameters
        # list.
        self.sim_hdl_toplevel = hdl_toplevel
        self.hdl_toplevel_library: str = hdl_toplevel_library
        self.hdl_toplevel_lang = self._check_hdl_toplevel_lang(hdl_toplevel_lang)
        if gpi_interfaces:
            self.gpi_interfaces = gpi_interfaces
        else:
            self.gpi_interfaces = []
            for gpi_if in self.supported_gpi_interfaces.values():
                self.gpi_interfaces.append(gpi_if[0])

        self.test_args = list(test_args)
        self.plusargs = list(plusargs)
        self.env = dict(extra_env)

        if testcase is not None:
            if isinstance(testcase, str):
                self.env["TESTCASE"] = testcase
            else:
                self.env["TESTCASE"] = ",".join(testcase)

        if seed is not None:
            self.env["RANDOM_SEED"] = str(seed)

        self.waves = bool(waves)
        self.gui = bool(gui)

        if verbose is not None:
            self.verbose = verbose

        # When using pytest, use test name as result file name
        pytest_current_test = os.getenv("PYTEST_CURRENT_TEST", "")
        if pytest_current_test:
            self.current_test_name = pytest_current_test.split(":")[-1].split(" ")[0]
            results_xml_name = f"{self.current_test_name}.{results_xml}"
        else:
            self.current_test_name = "test"
            results_xml_name = results_xml

        results_xml_file = Path(self.test_dir) / results_xml_name

        with suppress(OSError):
            os.remove(results_xml_file)

        # transport the settings to cocotb via environment variables
        self._set_env()
        self.env["COCOTB_RESULTS_FILE"] = str(results_xml_file)

        cmds: Sequence[Command] = self._test_command()
        self._execute(cmds, cwd=self.test_dir)

        # Only when running under pytest, check the results file here,
        # potentially raising an exception with failing testcases,
        # otherwise return the results file for later analysis.
        if pytest_current_test:
            check_results_file(results_xml_file)

        print(f"INFO: Results file: {results_xml_file}")
        return results_xml_file

    @staticmethod
    def _get_include_options(self, includes: Sequence[PathLike]) -> Command:
        """Return simulator-specific formatted option strings with *includes* directories."""

        raise NotImplementedError()

    @staticmethod
    def _get_define_options(self, defines: Mapping[str, object]) -> Command:
        """Return simulator-specific formatted option strings with *defines* macros."""

        raise NotImplementedError()

    @abc.abstractmethod
    def _get_parameter_options(self, parameters: Mapping[str, object]) -> Command:
        """Return simulator-specific formatted option strings with *parameters*/generics."""

        raise NotImplementedError()

    def _execute(self, cmds: Sequence[Command], cwd: PathLike) -> None:

        __tracebackhide__ = True  # Hide the traceback when using PyTest.

        for cmd in cmds:
            print(f"INFO: Running command {shlex_join(cmd)} in directory {cwd}")

            # TODO: create a thread to handle stderr and log as error?
            # TODO: log forwarding

            process = subprocess.run(cmd, cwd=cwd, env=self.env)

            if process.returncode != 0:
                raise SystemExit(
                    f"Process {process.args[0]!r} terminated with error {process.returncode}"
                )


def get_results(results_xml_file: Path) -> Tuple[int, int]:
    """Return number of tests and fails in *results_xml_file*.

    Returns:
        Tuple of number of tests and number of fails.

    Raises:
        SystemExit: *results_xml_file* is non-existent.
    """

    __tracebackhide__ = True  # Hide the traceback when using PyTest.

    if not results_xml_file.is_file():
        raise SystemExit(
            f"ERROR: Simulation terminated abnormally. Results file {results_xml_file} not found."
        )

    num_tests = 0
    num_failed = 0

    tree = ET.parse(results_xml_file)
    for ts in tree.iter("testsuite"):
        for tc in ts.iter("testcase"):
            num_tests += 1
            for _ in tc.iter("failure"):
                num_failed += 1

    return (num_tests, num_failed)


def check_results_file(results_xml_file: Path) -> None:
    """Raise exception if *results_xml_file* does not exist or contains failed tests.

    Raises:
        SystemExit: *results_xml_file* is non-existent or contains fails.
    """

    __tracebackhide__ = True  # Hide the traceback when using PyTest.

    (num_tests, num_failed) = get_results(results_xml_file)

    if num_failed:
        raise SystemExit(f"ERROR: Failed {num_failed} of {num_tests} tests.")


def outdated(output: Path, dependencies: Sequence[Path]) -> bool:
    """Return ``True`` if any source files in *dependencies* are newer than the *output* directory.

    Returns:
        ``True`` if any source files are newer, ``False`` otherwise.
    """

    if not output.is_file():
        return True

    output_mtime = output.stat().st_mtime

    dep_mtime = 0.0
    for dependency in dependencies:
        mtime = dependency.stat().st_mtime
        if mtime > dep_mtime:
            dep_mtime = mtime

    return dep_mtime > output_mtime


def get_abs_path(path: PathLike) -> Path:
    """Return *path* in absolute form."""

    path = Path(path)
    if path.is_absolute():
        return path.resolve()
    else:
        return Path(Path.cwd() / path).resolve()


def get_abs_paths(paths: Sequence[PathLike]) -> List[Path]:
    """Return list of *paths* in absolute form."""

    return [get_abs_path(path) for path in paths]


class Icarus(Simulator):
    supported_gpi_interfaces = {"verilog": ["vpi"]}

    @staticmethod
    def _simulator_in_path() -> None:
        if shutil.which("iverilog") is None:
            raise SystemExit("ERROR: iverilog executable not found!")

    @staticmethod
    def _get_include_options(includes: Sequence[PathLike]) -> Command:
        return [f"-I{include}" for include in includes]

    @staticmethod
    def _get_define_options(defines: Mapping[str, object]) -> Command:
        return [f"-D{name}={value}" for name, value in defines.items()]

    def _get_parameter_options(self, parameters: Mapping[str, object]) -> Command:
        assert self.hdl_toplevel is not None
        return [
            f"-P{self.hdl_toplevel}.{name}={value}"
            for name, value in parameters.items()
        ]

    @property
    def sim_file(self) -> Path:
        return self.build_dir / "sim.vvp"

    def _test_command(self) -> List[Command]:

        return [
            [
                "vvp",
                "-M",
                cocotb.config.libs_dir,
                "-m",
                cocotb.config.lib_name("vpi", "icarus"),
            ]
            + self.test_args
            + [str(self.sim_file)]
            + self.plusargs
        ]

    def _build_command(self) -> List[Command]:

        if self.vhdl_sources:
            raise ValueError(
                f"{type(self).__qualname__}: Simulator does not support VHDL"
            )

        cmds = []
        if outdated(self.sim_file, self.verilog_sources) or self.always:

            cmds = [
                ["iverilog", "-o", str(self.sim_file), "-D", "COCOTB_SIM=1", "-g2012"]
                + self._get_define_options(self.defines)
                + self._get_include_options(self.includes)
                + self._get_parameter_options(self.parameters)
                + self.build_args
                + [str(source_file) for source_file in self.verilog_sources]
            ]

        else:
            print("WARNING: Skipping compilation of", self.sim_file)

        return cmds


class Questa(Simulator):
    supported_gpi_interfaces = {"verilog": ["vpi"], "vhdl": ["fli", "vhpi"]}

    @staticmethod
    def _simulator_in_path() -> None:
        if shutil.which("vsim") is None:
            raise SystemExit("ERROR: vsim executable not found!")

    @staticmethod
    def _get_include_options(includes: Sequence[PathLike]) -> Command:
        return [f"+incdir+{as_tcl_value(str(include))}" for include in includes]

    @staticmethod
    def _get_define_options(defines: Mapping[str, object]) -> Command:
        return [
            f"+define+{as_tcl_value(name)}={as_tcl_value(str(value))}"
            for name, value in defines.items()
        ]

    @staticmethod
    def _get_parameter_options(parameters: Mapping[str, object]) -> Command:
        return [f"-g{name}={value}" for name, value in parameters.items()]

    def _build_command(self) -> List[Command]:

        cmds = []

        if self.vhdl_sources:
            cmds.append(["vlib", as_tcl_value(self.hdl_library)])
            cmds.append(
                ["vcom"]
                + ["-work", as_tcl_value(self.hdl_library)]
                + [as_tcl_value(v) for v in self.build_args]
                + [as_tcl_value(str(v)) for v in self.vhdl_sources]
            )

        if self.verilog_sources:
            cmds.append(["vlib", as_tcl_value(self.hdl_library)])
            cmds.append(
                ["vlog"]
                + ([] if self.always else ["-incr"])
                + ["-work", as_tcl_value(self.hdl_library)]
                + ["+define+COCOTB_SIM"]
                + ["-sv"]
                + self._get_define_options(self.defines)
                + self._get_include_options(self.includes)
                + [as_tcl_value(v) for v in self.build_args]
                + [as_tcl_value(str(v)) for v in self.verilog_sources]
            )

        return cmds

    def _test_command(self) -> List[Command]:

        cmds = []

        do_script = ""
        if self.waves:
            do_script += "log -recursive /*;"

        if not self.gui:
            do_script += "run -all; quit"

        gpi_if_entry = self.gpi_interfaces[0]
        gpi_if_entry_lib_path = cocotb.config.lib_name_path(gpi_if_entry, "questa")

        if gpi_if_entry == "fli":
            lib_opts = [
                "-foreign",
                "cocotb_init "
                + as_tcl_value(cocotb.config.lib_name_path("fli", "questa")),
            ]
        elif gpi_if_entry == "vhpi":
            lib_opts = ["-voptargs=-access=rw+/."]
            lib_opts += [
                "-foreign",
                "vhpi_startup_routines_bootstrap "
                + as_tcl_value(cocotb.config.lib_name_path("vhpi", "questa")),
            ]
        else:
            lib_opts = [
                "-pli",
                as_tcl_value(cocotb.config.lib_name_path("vpi", "questa")),
            ]

        if not Path(gpi_if_entry_lib_path).is_file():
            raise SystemExit(
                "ERROR: cocotb was not installed with a {gpi_if_entry} library."
            )

        cmds.append(
            ["vsim"]
            + ["-gui" if self.gui else "-c"]
            + ["-onfinish", "stop" if self.gui else "exit"]
            + lib_opts
            + [as_tcl_value(v) for v in self.test_args]
            + [as_tcl_value(v) for v in self._get_parameter_options(self.parameters)]
            + [as_tcl_value(f"{self.hdl_toplevel_library}.{self.sim_hdl_toplevel}")]
            + [as_tcl_value(v) for v in self.plusargs]
            + ["-do", do_script]
        )

        gpi_extra_list = []
        for gpi_if in self.gpi_interfaces[1:]:
            gpi_if_lib_path = cocotb.config.lib_name_path(gpi_if, "questa")
            if Path(gpi_if_lib_path).is_file():
                gpi_extra_list.append(
                    cocotb.config.lib_name_path(gpi_if, "questa")
                    + f":cocotb{gpi_if}_entry_point"
                )
            else:
                print("WARNING: {gpi_if_lib_path} library not found.")
        self.env["GPI_EXTRA"] = ",".join(gpi_extra_list)

        return cmds


class Ghdl(Simulator):
    supported_gpi_interfaces = {"vhdl": ["vpi"]}

    @staticmethod
    def _simulator_in_path() -> None:
        if shutil.which("ghdl") is None:
            raise SystemExit("ERROR: ghdl executable not found!")

    @staticmethod
    def _get_parameter_options(parameters: Mapping[str, object]) -> Command:
        return [f"-g{name}={value}" for name, value in parameters.items()]

    def _build_command(self) -> List[Command]:

        if self.verilog_sources:
            raise ValueError(
                f"{type(self).__qualname__}: Simulator does not support Verilog"
            )

        cmds = [
            ["ghdl", "-i"]
            + [f"--work={self.hdl_library}"]
            + self.build_args
            + [str(source_file) for source_file in self.vhdl_sources]
        ]

        if self.hdl_toplevel is not None:
            cmds += [
                ["ghdl", "-m"]
                + [f"--work={self.hdl_library}"]
                + self.build_args
                + [self.hdl_toplevel]
            ]

        return cmds

    def _test_command(self) -> List[Command]:

        cmds = [
            ["ghdl", "-r"]
            + [f"--work={self.hdl_toplevel_library}"]
            + self.test_args
            + [self.sim_hdl_toplevel]
            + ["--vpi=" + cocotb.config.lib_name_path("vpi", "ghdl")]
            + self.plusargs
            + self._get_parameter_options(self.parameters)
        ]

        return cmds


class Riviera(Simulator):
    supported_gpi_interfaces = {"verilog": ["vpi"], "vhdl": ["vhpi"]}

    @staticmethod
    def _simulator_in_path() -> None:
        if shutil.which("vsimsa") is None:
            raise SystemExit("ERROR: vsimsa executable not found!")

    @staticmethod
    def _get_include_options(includes: Sequence[PathLike]) -> Command:
        return [f"+incdir+{as_tcl_value(str(include))}" for include in includes]

    @staticmethod
    def _get_define_options(defines: Mapping[str, object]) -> Command:
        return [
            f"+define+{as_tcl_value(name)}={as_tcl_value(str(value))}"
            for name, value in defines.items()
        ]

    @staticmethod
    def _get_parameter_options(parameters: Mapping[str, object]) -> Command:
        return [f"-g{name}={value}" for name, value in parameters.items()]

    def _build_command(self) -> List[Command]:

        do_script = "\nonerror {\n quit -code 1 \n} \n"

        out_file = self.build_dir / self.hdl_library / f"{self.hdl_library}.lib"

        if outdated(out_file, self.verilog_sources + self.vhdl_sources) or self.always:

            do_script += "alib {RTL_LIBRARY} \n".format(
                RTL_LIBRARY=as_tcl_value(self.hdl_library)
            )

            if self.vhdl_sources:
                do_script += (
                    "acom -work {RTL_LIBRARY} {EXTRA_ARGS} {VHDL_SOURCES}\n".format(
                        RTL_LIBRARY=as_tcl_value(self.hdl_library),
                        VHDL_SOURCES=" ".join(
                            as_tcl_value(str(v)) for v in self.vhdl_sources
                        ),
                        EXTRA_ARGS=" ".join(as_tcl_value(v) for v in self.build_args),
                    )
                )

            if self.verilog_sources:
                do_script += "alog -work {RTL_LIBRARY} +define+COCOTB_SIM -sv {DEFINES} {INCDIR} {EXTRA_ARGS} {VERILOG_SOURCES} \n".format(
                    RTL_LIBRARY=as_tcl_value(self.hdl_library),
                    VERILOG_SOURCES=" ".join(
                        as_tcl_value(str(v)) for v in self.verilog_sources
                    ),
                    DEFINES=" ".join(self._get_define_options(self.defines)),
                    INCDIR=" ".join(self._get_include_options(self.includes)),
                    EXTRA_ARGS=" ".join(as_tcl_value(v) for v in self.build_args),
                )
        else:
            print("WARNING: Skipping compilation of", out_file)

        do_file = tempfile.NamedTemporaryFile(delete=False)
        do_file.write(do_script.encode())
        do_file.close()

        return [["vsimsa"] + ["-do"] + ["do"] + [do_file.name]]

    def _test_command(self) -> List[Command]:

        do_script = "\nonerror {\n quit -code 1 \n} \n"

        if self.hdl_toplevel_lang == "vhdl":
            do_script += "asim +access +w -interceptcoutput -O2 -loadvhpi {EXT_NAME} {EXTRA_ARGS} {TOPLEVEL} {PLUSARGS}\n".format(
                TOPLEVEL=as_tcl_value(
                    f"{self.hdl_toplevel_library}.{self.sim_hdl_toplevel}"
                ),
                EXT_NAME=as_tcl_value(cocotb.config.lib_name_path("vhpi", "riviera")),
                EXTRA_ARGS=" ".join(
                    as_tcl_value(v)
                    for v in (
                        self.test_args + self._get_parameter_options(self.parameters)
                    )
                ),
                PLUSARGS=" ".join(as_tcl_value(v) for v in self.plusargs),
            )

            self.env["GPI_EXTRA"] = (
                cocotb.config.lib_name_path("vpi", "riviera") + ":cocotbvpi_entry_point"
            )
        else:
            do_script += "asim +access +w -interceptcoutput -O2 -pli {EXT_NAME} {EXTRA_ARGS} {TOPLEVEL} {PLUSARGS} \n".format(
                TOPLEVEL=as_tcl_value(
                    f"{self.hdl_toplevel_library}.{self.sim_hdl_toplevel}"
                ),
                EXT_NAME=as_tcl_value(cocotb.config.lib_name_path("vpi", "riviera")),
                EXTRA_ARGS=" ".join(
                    as_tcl_value(v)
                    for v in (
                        self.test_args + self._get_parameter_options(self.parameters)
                    )
                ),
                PLUSARGS=" ".join(as_tcl_value(v) for v in self.plusargs),
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
    supported_gpi_interfaces = {"verilog": ["vpi"]}

    def _simulator_in_path(self) -> None:
        executable = shutil.which("verilator")
        if executable is None:
            raise SystemExit("ERROR: verilator executable not found!")
        self.executable: str = executable

    @staticmethod
    def _get_include_options(includes: Sequence[PathLike]) -> Command:
        return [f"-I{include}" for include in includes]

    @staticmethod
    def _get_define_options(defines: Mapping[str, object]) -> Command:
        return [f"-D{name}={value}" for name, value in defines.items()]

    @staticmethod
    def _get_parameter_options(parameters: Mapping[str, object]) -> Command:
        return [f"-G{name}={value}" for name, value in parameters.items()]

    def _build_command(self) -> List[Command]:

        if self.vhdl_sources:
            raise ValueError(
                f"{type(self).__qualname__}: Simulator does not support VHDL"
            )

        if self.hdl_toplevel is None:
            raise ValueError(
                f"{type(self).__qualname__}: Simulator requires the hdl_toplevel parameter to be specified"
            )

        # TODO: set "--debug" if self.verbose
        # TODO: support "--always"

        verilator_cpp = str(
            Path(cocotb.__file__).parent
            / "share"
            / "lib"
            / "verilator"
            / "verilator.cpp"
        )

        cmds = []
        cmds.append(
            [
                "perl",
                self.executable,
                "-cc",
                "--exe",
                "-Mdir",
                str(self.build_dir),
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
            + self.build_args
            + self._get_define_options(self.defines)
            + self._get_include_options(self.includes)
            + self._get_parameter_options(self.parameters)
            + [verilator_cpp]
            + [str(source_file) for source_file in self.verilog_sources]
        )

        cmds.append(["make", "-C", str(self.build_dir), "-f", "Vtop.mk"])

        return cmds

    def _test_command(self) -> List[Command]:
        out_file = self.build_dir / self.sim_hdl_toplevel
        return [[str(out_file)] + self.plusargs]


class Xcelium(Simulator):
    supported_gpi_interfaces = {"verilog": ["vpi"], "vhdl": ["vhpi"]}

    @staticmethod
    def _simulator_in_path() -> None:
        if shutil.which("xrun") is None:
            raise SystemExit("ERROR: xrun executable not found!")

    @staticmethod
    def _get_include_options(includes: Sequence[PathLike]) -> Command:
        return [f"-incdir {include}" for include in includes]

    @staticmethod
    def _get_define_options(defines: Mapping[str, object]) -> Command:
        return [f"-define {name}={value}" for name, value in defines.items()]

    @staticmethod
    def _get_parameter_options(parameters: Mapping[str, object]) -> Command:
        return [f'-gpg "{name} => {value}"' for name, value in parameters.items()]

    def _build_command(self) -> List[Command]:
        self.env["CDS_AUTO_64BIT"] = "all"

        verbosity_opts = []
        if self.verbose:
            verbosity_opts += ["-messages"]
            verbosity_opts += ["-status"]
            verbosity_opts += ["-gverbose"]  # print assigned generics/parameters
            verbosity_opts += ["-pliverbose"]
            verbosity_opts += ["-plidebug"]  # Enhance the profile output with PLI info
            verbosity_opts += [
                "-plierr_verbose"
            ]  # Expand handle info in PLI/VPI/VHPI messages

        else:
            verbosity_opts += ["-quiet"]
            verbosity_opts += ["-plinowarn"]

        cmds = [
            ["xrun"]
            + ["-logfile"]
            + ["xrun_build.log"]
            + ["-elaborate"]
            + ["-xmlibdirname"]
            + [f"{self.build_dir}/xrun_snapshot"]
            + ["-licqueue"]
            + (["-clean"] if self.always else [])
            + verbosity_opts
            # + ["-vpicompat 1800v2005"]  # <1364v1995|1364v2001|1364v2005|1800v2005> Specify the IEEE VPI
            + ["-access +rwc"]
            + ["-loadvpi"]
            # always start with VPI on Xcelium
            + [
                cocotb.config.lib_name_path("vpi", "xcelium")
                + ":vlog_startup_routines_bootstrap"
            ]
            + [f"-work {self.hdl_library}"]
            + self.build_args
            + ["-define COCOTB_SIM"]
            + self._get_include_options(self.includes)
            + self._get_define_options(self.defines)
            + self._get_parameter_options(self.parameters)
            + [f"-top {self.hdl_toplevel}"]
            + [
                str(source_file)
                for source_file in self.vhdl_sources + self.verilog_sources
            ]
        ]

        return cmds

    def _test_command(self) -> List[Command]:
        self.env["CDS_AUTO_64BIT"] = "all"

        verbosity_opts = []
        if self.verbose:
            verbosity_opts += ["-messages"]
            verbosity_opts += ["-status"]
            verbosity_opts += ["-gverbose"]  # print assigned generics/parameters
            verbosity_opts += ["-pliverbose"]
            verbosity_opts += ["-plidebug"]  # Enhance the profile output with PLI info
            verbosity_opts += [
                "-plierr_verbose"
            ]  # Expand handle info in PLI/VPI/VHPI messages

        else:
            verbosity_opts += ["-quiet"]
            verbosity_opts += ["-plinowarn"]

        tmpdir = f"implicit_tmpdir_{self.current_test_name}"

        if self.hdl_toplevel_lang == "vhdl":
            xrun_top = ":"
        else:
            xrun_top = self.sim_hdl_toplevel

        cmds = [["mkdir", "-p", tmpdir]]
        cmds += [
            ["xrun"]
            + ["-logfile"]
            + [f"xrun_{self.current_test_name}.log"]
            + ["-xmlibdirname"]
            + [f"{self.build_dir}/xrun_snapshot"]
            + ["-cds_implicit_tmpdir"]
            + [tmpdir]
            + ["-licqueue"]
            + verbosity_opts
            + ["-R"]
            + self.test_args
            + self.plusargs
            + ["-gui" if self.gui else ""]
            + ["-input"]
            + [
                f'-input "@database -open cocotb_waves -default" '
                f'-input "@probe -database cocotb_waves -create {xrun_top} -all -depth all" '
                f'-input "@run" '
                f'-input "@exit" '
                if self.waves
                else "@run; exit;"
            ]
        ]
        self.env["GPI_EXTRA"] = (
            cocotb.config.lib_name_path("vhpi", "xcelium") + ":cocotbvhpi_entry_point"
        )

        return cmds


def get_runner(simulator_name: str) -> Simulator:
    """Return the *simulator_name* instance."""

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
        return supported_sims[simulator_name]()
    except KeyError:
        raise ValueError(
            f"Simulator {simulator_name!r} is not in supported list: {', '.join(supported_sims)}"
        ) from None
