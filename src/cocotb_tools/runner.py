# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Build HDL and run cocotb tests."""

# TODO: maybe do globbing and expanduser/expandvars in --include, --vhdl-sources, --verilog-sources
# TODO: create a short README and a .gitignore (content: "*") in both build_dir and test_dir? (Some other tools do this.)
# TODO: support timescale on all simulators
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
from typing import Dict, List, Mapping, Optional, Sequence, TextIO, Tuple, Type, Union
from xml.etree import ElementTree as ET

import find_libpython

import cocotb_tools.config

PathLike = Union["os.PathLike[str]", str]
Command = List[str]
Timescale = Tuple[str, str]

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


class VHDL(str):
    """Tags source files and build arguments to :meth:`~cocotb_tools.runner.Simulator.build` as VHDL-specific."""


class Verilog(str):
    """Tags source files and build arguments to :meth:`~cocotb_tools.runner.Simulator.build` as Verilog-specific."""


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
            if self.vhdl_sources and not self.verilog_sources and not self.sources:
                lang = "vhdl"
            elif self.verilog_sources and not self.vhdl_sources and not self.sources:
                lang = "verilog"
            elif self.sources and not self.vhdl_sources and not self.verilog_sources:
                if is_vhdl_source(self.sources[-1]):
                    lang = "vhdl"
                elif is_verilog_source(self.sources[-1]):
                    lang = "verilog"
                else:
                    raise UnknownFileExtension(self.sources[-1])
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
            libpython_path = find_libpython.find_libpython()
            if not libpython_path:
                raise ValueError(
                    "Unable to find libpython, please make sure the appropriate libpython is installed"
                )
            self.env["LIBPYTHON_LOC"] = libpython_path

        self.env["PATH"] += os.pathsep + str(cocotb_tools.config.libs_dir)
        self.env["PYTHONPATH"] = os.pathsep.join(sys.path)
        self.env["PYTHONHOME"] = sys.prefix
        self.env["TOPLEVEL"] = self.sim_hdl_toplevel
        self.env["MODULE"] = self.test_module
        self.env["TOPLEVEL_LANG"] = self.hdl_toplevel_lang

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
        sources: Sequence[Union[PathLike, VHDL, Verilog]] = [],
        includes: Sequence[PathLike] = [],
        defines: Mapping[str, object] = {},
        parameters: Mapping[str, object] = {},
        build_args: Sequence[Union[str, VHDL, Verilog]] = [],
        hdl_toplevel: Optional[str] = None,
        always: bool = False,
        build_dir: PathLike = "sim_build",
        clean: bool = False,
        verbose: bool = False,
        timescale: Optional[Timescale] = None,
        waves: Optional[bool] = None,
        log_file: Optional[PathLike] = None,
    ) -> None:
        """Build the HDL sources.

        With mixed language simulators, *sources* will be built,
        followed by *vhdl_sources*, then *verilog_sources*.
        With simulators that only support either VHDL or Verilog, *sources* will be built,
        followed by *vhdl_sources* and *verilog_sources*, respectively.

        If your source files use an atypical file extension,
        use :class:`VHDL` and :class:`Verilog` to tag the path as a VHDL or Verilog source file, respectively.
        If the filepaths aren't tagged, the extension is used to determine if they are VHDL or Verilog files.

        +----------+------------------------------------+
        | Language | File Extensions                    |
        +==========+====================================+
        | VHDL     | ``.vhd``, ``.vhdl``                |
        +----------+------------------------------------+
        | Verilog  | ``.v``, ``.sv``, ``.vh``, ``.svh`` |
        +----------+------------------------------------+


        .. code-block:: python3

            runner.build(
                sources=[
                    VHDL("/my/file.is_actually_vhdl"),
                    Verilog("/other/file.verilog"),
                ],
            )

        The same tagging works for *build_args*.
        Tagged *build_args* only supply that option to the compiler when building the source file for the tagged language.
        Non-tagged *build_args* are supplied when compiling any language.

        Args:
            hdl_library: The library name to compile into.
            verilog_sources: Verilog source files to build.
            vhdl_sources: VHDL source files to build.
            sources: Language-agnostic list of source files to build.
            includes: Verilog include directories.
            defines: Defines to set.
            parameters: Verilog parameters or VHDL generics.
            build_args: Extra build arguments for the simulator.
            hdl_toplevel: The name of the HDL toplevel module.
            always: Always run the build step.
            build_dir: Directory to run the build step in.
            clean: Delete *build_dir* before building.
            verbose: Enable verbose messages.
            timescale: Tuple containing time unit and time precision for simulation.
            waves: Record signal traces.
            log_file: File to write the build log to.

        .. deprecated:: 2.0

            Uses of the *verilog_sources* and *vhdl_sources* parameters should be replaced with the language-agnostic *sources* argument.
        """

        self.clean: bool = clean
        self.build_dir = get_abs_path(build_dir)
        if self.clean:
            self.rm_build_folder(self.build_dir)
        os.makedirs(self.build_dir, exist_ok=True)

        # note: to avoid mutating argument defaults, we ensure that no value
        # is written without a copy. This is much more concise and leads to
        # a better docstring than using `None` as a default in the parameters
        # list.
        self.hdl_library: str = hdl_library
        if verilog_sources:
            warnings.warn(
                "Simulator.build *verilog_sources* parameter is deprecated. Use the language-agnostic *sources* parameter instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        self.verilog_sources: List[Path] = get_abs_paths(verilog_sources)
        if vhdl_sources:
            warnings.warn(
                "Simulator.build *vhdl_sources* parameter is deprecated. Use the language-agnostic *sources* parameter instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        self.vhdl_sources: List[Path] = get_abs_paths(vhdl_sources)
        self.sources: List[Path] = get_abs_paths(sources)
        self.includes: List[Path] = get_abs_paths(includes)
        self.defines = dict(defines)
        self.parameters = dict(parameters)
        self.build_args = list(build_args)
        self.always: bool = always
        self.hdl_toplevel: Optional[str] = hdl_toplevel
        self.verbose: bool = verbose
        self.timescale: Optional[Timescale] = timescale
        self.log_file: Optional[PathLike] = log_file

        self.waves = bool(waves)

        self.env.update(os.environ)

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
        results_xml: Optional[str] = None,
        pre_cmd: List[str] = [],
        verbose: bool = False,
        timescale: Optional[Timescale] = None,
        log_file: Optional[PathLike] = None,
        test_filter: Optional[str] = None,
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
            test_args: A list of extra arguments for the simulator.
            plusargs: 'plusargs' to set for the simulator.
            extra_env: Extra environment variables to set.
            waves: Record signal traces.
            gui: Run with simulator GUI.
            parameters: Verilog parameters or VHDL generics.
            build_dir: Directory the build step has been run in.
            test_dir: Directory to run the tests in.
            results_xml: Name of xUnit XML file to store test results in.
                If an absolute path is provided it will be used as-is,
                ``{build_dir}/results.xml`` otherwise.
                This argument should not be set when run with ``pytest``.
            verbose: Enable verbose messages.
            pre_cmd: Commands to run before simulation begins.
                Typically Tcl commands for simulators that support them.
            timescale: Tuple containing time unit and time precision for simulation.
            log_file: File to write the test log to.
            test_filter: Regular expression which matches test names.
                Only matched tests are run if this argument if given.

        Returns:
            The absolute location of the results XML file which can be
            defined by the *results_xml* argument.
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

        self.pre_cmd = pre_cmd

        self.test_args = list(test_args)
        self.plusargs = list(plusargs)
        self.env = dict(extra_env)

        if testcase is not None:
            if isinstance(testcase, str):
                self.env["TESTCASE"] = testcase
            else:
                self.env["TESTCASE"] = ",".join(testcase)

        if test_filter is not None:
            self.env["COCOTB_TEST_FILTER"] = test_filter

        if seed is not None:
            self.env["RANDOM_SEED"] = str(seed)

        self.log_file = log_file
        self.waves = bool(waves)
        self.gui = bool(gui)
        self.timescale: Optional[Timescale] = timescale

        if verbose is not None:
            self.verbose = verbose

        # When using pytest, use test name as result file name
        pytest_current_test = os.getenv("PYTEST_CURRENT_TEST", None)
        test_dir_path = Path(self.test_dir)
        self.current_test_name = "test"
        if results_xml is not None:
            # PYTEST_CURRENT_TEST only allowed when results_xml is not set
            assert not pytest_current_test
            results_xml_path = Path(results_xml)
            if results_xml_path.is_absolute():
                results_xml_file = results_xml_path
            else:
                results_xml_file = test_dir_path / results_xml_path
        elif pytest_current_test is not None:
            self.current_test_name = pytest_current_test.split(":")[-1].split(" ")[0]
            results_xml_file = test_dir_path / f"{self.current_test_name}.{results_xml}"
        else:
            results_xml_file = test_dir_path / "results.xml"

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

        if self.log_file is None:
            self._execute_cmds(cmds, cwd)
        else:
            with open(self.log_file, "w") as f:
                self._execute_cmds(cmds, cwd, f)

    def _execute_cmds(
        self, cmds: Sequence[Command], cwd: PathLike, stdout: Optional[TextIO] = None
    ) -> None:
        __tracebackhide__ = True  # Hide the traceback when using PyTest.

        for cmd in cmds:
            print(f"INFO: Running command {shlex_join(cmd)} in directory {cwd}")

            # TODO: create a thread to handle stderr and log as error?
            # TODO: log forwarding

            stderr = None if stdout is None else subprocess.STDOUT
            subprocess.run(
                cmd, cwd=cwd, env=self.env, check=True, stdout=stdout, stderr=stderr
            )

    def rm_build_folder(self, build_dir: Path):
        if os.path.isdir(build_dir):
            print("Removing:", build_dir)
            shutil.rmtree(build_dir, ignore_errors=True)


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


_verilog_extensions = (".v", ".sv", ".vh", ".svh")
_vhdl_extensions = (".vhd", ".vhdl")

_vhdl_extensions_s = ", ".join(f"`{c}`" for c in _vhdl_extensions)
_verilog_extensions_s = ", ".join(f"`{c}`" for c in _verilog_extensions)


class UnknownFileExtension(ValueError):
    def __init__(self, source: PathLike) -> None:
        super().__init__(
            f"Can't determine if {source} is a VHDL or Verilog file. "
            f"Use a standard file extension ({_vhdl_extensions_s} for VHDL files and {_verilog_extensions_s} for Verilog files) "
            "or tag the source with `VHDL(source)` or `Verilog(source)`."
        )


def is_vhdl_source(source: PathLike) -> bool:
    if isinstance(source, VHDL):
        return True
    source_as_path = Path(source)
    if source_as_path.suffix in _vhdl_extensions:
        return True
    return False


def is_verilog_source(source: PathLike) -> bool:
    if isinstance(source, Verilog):
        return True
    source_as_path = Path(source)
    if source_as_path.suffix in _verilog_extensions:
        return True
    return False


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

    def _create_cmd_file(self) -> None:
        with open(self.cmds_file, "w") as f:
            f.write("+timescale+{}/{}\n".format(*self.timescale))

    def _create_iverilog_dump_file(self) -> None:
        dumpfile_path = Path(self.build_dir, f"{self.hdl_toplevel}.fst").as_posix()
        with open(self.iverilog_dump_file, "w") as f:
            f.write("module cocotb_iverilog_dump();\n")
            f.write("initial begin\n")
            f.write(f'    $dumpfile("{dumpfile_path}");\n')
            f.write(f"    $dumpvars(0, {self.hdl_toplevel});\n")
            f.write("end\n")
            f.write("endmodule\n")

    @property
    def sim_file(self) -> Path:
        return self.build_dir / "sim.vvp"

    @property
    def iverilog_dump_file(self) -> Path:
        return self.build_dir / "cocotb_iverilog_dump.v"

    @property
    def cmds_file(self) -> Path:
        return self.build_dir / "cmds.f"

    def _test_command(self) -> List[Command]:
        plusargs = self.plusargs
        if self.waves:
            plusargs += ["-fst"]

        if self.pre_cmd:
            print("WARNING: pre_cmd is not implemented for Icarus Verilog.")

        return [
            [
                "vvp",
                "-M",
                str(cocotb_tools.config.libs_dir),
                "-m",
                cocotb_tools.config.lib_name("vpi", "icarus"),
            ]
            + self.test_args
            + [str(self.sim_file)]
            + plusargs
        ]

    def _build_command(self) -> List[Command]:
        for source in self.sources:
            if not is_verilog_source(source):
                raise ValueError(
                    f"{type(self).__qualname__} only supports Verilog. {str(source)!r} cannot be compiled."
                )
        for arg in self.build_args:
            if type(arg) not in (str, Verilog):
                print(
                    f"WARNING: {type(self).__qualname__} only supports Verilog. build_args {arg!r} will not be applied."
                )

        build_args = list(self.build_args)
        if self.waves:
            self._create_iverilog_dump_file()
            build_args += ["-s", "cocotb_iverilog_dump"]

        if self.timescale is not None:
            self._create_cmd_file()
            build_args += ["-f", str(self.cmds_file)]

        cmds = []
        sources = [
            source for source in self.sources if is_verilog_source(source)
        ] + self.verilog_sources
        if outdated(self.sim_file, sources) or self.always:
            cmds = [
                [
                    "iverilog",
                    "-o",
                    str(self.sim_file),
                    "-s",
                    self.hdl_toplevel,
                    "-g2012",
                ]
                + self._get_define_options(self.defines)
                + self._get_include_options(self.includes)
                + self._get_parameter_options(self.parameters)
                + [arg for arg in build_args if type(arg) in (str, Verilog)]
                + [str(source_file) for source_file in sources]
                + [
                    str(source_file)
                    for source_file in [self.iverilog_dump_file]
                    if self.waves
                ]
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

        cmds.append(["vlib", as_tcl_value(self.hdl_library)])
        for source in self.sources:
            if is_vhdl_source(source):
                cmds.append(self._build_vhdl_command(source))
            elif is_verilog_source(source):
                cmds.append(self._build_verilog_command(source))
            else:
                raise UnknownFileExtension(source)
        for source in self.vhdl_sources:
            cmds.append(self._build_vhdl_command(source))
        for source in self.verilog_sources:
            cmds.append(self._build_verilog_command(source))

        return cmds

    def _build_vhdl_command(self, source: PathLike) -> Command:
        return (
            ["vcom"]
            + ["-work", as_tcl_value(self.hdl_library)]
            + [as_tcl_value(v) for v in self.build_args if type(v) in (str, VHDL)]
            + [as_tcl_value(str(source))]
        )

    def _build_verilog_command(self, source: PathLike) -> Command:
        return (
            ["vlog"]
            + ([] if self.always else ["-incr"])
            + ["-work", as_tcl_value(self.hdl_library)]
            + ["-sv"]
            + self._get_define_options(self.defines)
            + self._get_include_options(self.includes)
            + [as_tcl_value(v) for v in self.build_args if type(v) in (str, Verilog)]
            + [as_tcl_value(str(source))]
        )

    def _test_command(self) -> List[Command]:
        cmds = []

        if self.pre_cmd:
            self.pre_cmd = ["-do"] + self.pre_cmd

        do_script = ""
        if self.waves:
            do_script += "log -recursive /*;"

        if not self.gui:
            do_script += "run -all; quit"

        gpi_if_entry = self.gpi_interfaces[0]
        if gpi_if_entry == "fli":
            lib_opts = [
                "-foreign",
                "cocotb_init "
                + as_tcl_value(
                    cocotb_tools.config.lib_name_path("fli", "questa").as_posix()
                ),
            ]
        elif gpi_if_entry == "vhpi":
            lib_opts = ["-voptargs=-access=rw+/."]
            lib_opts += [
                "-foreign",
                "vhpi_startup_routines_bootstrap "
                + as_tcl_value(
                    cocotb_tools.config.lib_name_path("vhpi", "questa").as_posix()
                ),
            ]
        else:
            lib_opts = [
                "-pli",
                as_tcl_value(
                    cocotb_tools.config.lib_name_path("vpi", "questa").as_posix()
                ),
            ]

        cmds.append(
            ["vsim"]
            + ["-gui" if self.gui else "-c"]
            + ["-onfinish", "stop" if self.gui else "exit"]
            + lib_opts
            + [as_tcl_value(v) for v in self.test_args]
            + [as_tcl_value(v) for v in self._get_parameter_options(self.parameters)]
            + [as_tcl_value(f"{self.hdl_toplevel_library}.{self.sim_hdl_toplevel}")]
            + [as_tcl_value(v) for v in self.plusargs]
            + self.pre_cmd
            + ["-do", do_script]
        )

        gpi_extra_list = []
        for gpi_if in self.gpi_interfaces[1:]:
            gpi_if_lib_path = cocotb_tools.config.lib_name_path(gpi_if, "questa")
            if gpi_if_lib_path.is_file():
                gpi_extra_list.append(
                    gpi_if_lib_path.as_posix() + f":cocotb{gpi_if}_entry_point"
                )
            else:
                print("WARNING: {gpi_if_lib_path} library not found.")
        self.env["GPI_EXTRA"] = ",".join(gpi_extra_list)

        return cmds


class Ghdl(Simulator):
    supported_gpi_interfaces = {"vhdl": ["vpi"]}

    def _set_env(self) -> None:
        super()._set_env()
        if "COCOTB_TRUST_INERTIAL_WRITES" not in self.env:
            self.env["COCOTB_TRUST_INERTIAL_WRITES"] = "1"

    @staticmethod
    def _simulator_in_path() -> None:
        if shutil.which("ghdl") is None:
            raise SystemExit("ERROR: ghdl executable not found!")

    def _is_mcode_backend(self) -> bool:
        """Is GHDL using the mcode backend?"""
        result = subprocess.run(
            ["ghdl", "--version"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        return "mcode" in result.stdout

    @staticmethod
    def _get_parameter_options(parameters: Mapping[str, object]) -> Command:
        return [f"-g{name}={value}" for name, value in parameters.items()]

    def _build_command(self) -> List[Command]:
        for source in self.sources:
            if not is_vhdl_source(source):
                raise ValueError(
                    f"{type(self).__qualname__} only supports VHDL. {str(source)!r} cannot be compiled."
                )
        for arg in self.build_args:
            if type(arg) not in (str, VHDL):
                print(
                    f"WARNING: {type(self).__qualname__} only supports VHDL. build_args {arg!r} will not be applied."
                )

        cmds = [
            ["ghdl", "-i"]
            + [f"--work={self.hdl_library}"]
            + [arg for arg in self.build_args if type(arg) in (str, VHDL)]
            + [str(source) for source in self.sources if is_vhdl_source(source)]
            + [str(source) for source in self.vhdl_sources]
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
        if self.pre_cmd:
            print("WARNING: pre_cmd is not implemented for GHDL.")

        ghdl_run_args = self.test_args

        if self._is_mcode_backend() and self.timescale:
            _, precision = self.timescale
            # Convert the time precision to a format string supported by GHDL,
            # if possible.
            # GHDL only supports setting the time precision if the mcode backend
            # is used, using the --time-resolution argument causes GHDL to error
            # out otherwise.
            # https://ghdl.github.io/ghdl/using/InvokingGHDL.html#cmdoption-ghdl-time-resolution
            if precision == "1fs":
                ghdl_time_resolution = "fs"
            elif precision == "1ps":
                ghdl_time_resolution = "ps"
            elif precision == "1ns":
                ghdl_time_resolution = "ns"
            elif precision == "1us":
                ghdl_time_resolution = "us"
            elif precision == "1ms":
                ghdl_time_resolution = "ms"
            elif precision == "1s":
                ghdl_time_resolution = "sec"
            else:
                raise ValueError(
                    "GHDL only supports the following precisions in timescale: 1fs, 1ps, 1us, 1ms, 1s"
                )

            ghdl_run_args.append(f"--time-resolution={ghdl_time_resolution}")

        cmds = [
            ["ghdl", "-r"]
            + [f"--work={self.hdl_toplevel_library}"]
            + ghdl_run_args
            + [self.sim_hdl_toplevel]
            + ["--vpi=" + cocotb_tools.config.lib_name_path("vpi", "ghdl").as_posix()]
            + self.plusargs
            + self._get_parameter_options(self.parameters)
        ]

        return cmds


class Nvc(Simulator):
    supported_gpi_interfaces = {"vhdl": ["vhpi"]}

    def _set_env(self) -> None:
        super()._set_env()
        if "COCOTB_TRUST_INERTIAL_WRITES" not in self.env:
            self.env["COCOTB_TRUST_INERTIAL_WRITES"] = "1"

    @staticmethod
    def _simulator_in_path() -> None:
        if shutil.which("nvc") is None:
            raise SystemExit("ERROR: nvc executable not found!")

    @staticmethod
    def _get_parameter_options(parameters: Mapping[str, object]) -> Command:
        return [f"-g{name}={value}" for name, value in parameters.items()]

    def _build_command(self) -> List[Command]:
        for source in self.sources:
            if not is_vhdl_source(source):
                raise ValueError(
                    f"{type(self).__qualname__} only supports VHDL. {str(source)!r} cannot be compiled."
                )
        for arg in self.build_args:
            if type(arg) not in (str, VHDL):
                print(
                    f"WARNING: {type(self).__qualname__} only supports VHDL. build_args {arg!r} will not be applied."
                )

        cmds = [
            ["nvc", f"--work={self.hdl_library}"]
            + [arg for arg in self.build_args if type(arg) in (str, VHDL)]
            + ["-a"]
            + [str(source) for source in self.sources if is_vhdl_source(source)]
            + [str(source) for source in self.vhdl_sources]
        ]

        return cmds

    def _test_command(self) -> List[Command]:
        cmds = [
            ["nvc", f"--work={self.hdl_toplevel_library}"]
            + self.build_args
            + ["-e", self.sim_hdl_toplevel, "--no-save", "--jit"]
            + self._get_parameter_options(self.parameters)
            + ["-r"]
            + self.test_args
            + ["--load=" + cocotb_tools.config.lib_name_path("vhpi", "nvc").as_posix()]
            + self.plusargs
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
        do_script: List[str] = ["onerror {\n quit -code 1 \n}"]

        out_file = self.build_dir / self.hdl_library / f"{self.hdl_library}.lib"

        if outdated(out_file, self.verilog_sources + self.vhdl_sources) or self.always:
            do_script.append(f"alib {as_tcl_value(self.hdl_library)}")

            for source in self.sources:
                if is_verilog_source(source):
                    do_script.append(self._build_verilog_source(source))
                elif is_vhdl_source(source):
                    do_script.append(self._build_vhdl_source(source))
                else:
                    raise UnknownFileExtension(source)
            for source in self.vhdl_sources:
                do_script.append(self._build_vhdl_source(source))
            for source in self.verilog_sources:
                do_script.append(self._build_verilog_source(source))

        # Explicitly exit the script at the end. In batch mode, which is invoked
        # implicitly by redirecting STDOUT/STDERR of the alog/acom commands,
        # the tool exits by itself even without this 'exit' command -- but not
        # when running from an interactive terminal. Be explicit for predictable
        # behavior.
        do_script.append("exit")

        do_file = tempfile.NamedTemporaryFile(delete=False)
        do_file.write("\n".join(do_script).encode())
        do_file.close()

        return [["vsimsa"] + ["-do"] + ["do"] + [do_file.name]]

    def _build_vhdl_source(self, source: PathLike) -> str:
        return "acom -work {RTL_LIBRARY} {EXTRA_ARGS} {VHDL_SOURCES}".format(
            RTL_LIBRARY=as_tcl_value(self.hdl_library),
            VHDL_SOURCES=as_tcl_value(str(source)),
            EXTRA_ARGS=" ".join(
                as_tcl_value(v) for v in self.build_args if type(v) in (str, VHDL)
            ),
        )

    def _build_verilog_source(self, source: PathLike) -> str:
        return "alog -work {RTL_LIBRARY} -pli {EXT_NAME} -sv {DEFINES} {INCDIR} {EXTRA_ARGS} {VERILOG_SOURCES}".format(
            RTL_LIBRARY=as_tcl_value(self.hdl_library),
            EXT_NAME=as_tcl_value(
                cocotb_tools.config.lib_name_path("vpi", "riviera").as_posix()
            ),
            VERILOG_SOURCES=as_tcl_value(str(source)),
            DEFINES=" ".join(self._get_define_options(self.defines)),
            INCDIR=" ".join(self._get_include_options(self.includes)),
            EXTRA_ARGS=" ".join(
                as_tcl_value(v) for v in self.build_args if type(v) in (str, Verilog)
            ),
        )

    def _test_command(self) -> List[Command]:
        if self.pre_cmd:
            print("WARNING: pre_cmd is not implemented for Riviera.")

        do_script: str = "\nonerror {\n quit -code 1 \n} \n"

        if self.hdl_toplevel_lang == "vhdl":
            do_script += "asim +access +w_nets -interceptcoutput -loadvhpi {EXT_NAME} {EXTRA_ARGS} {TOPLEVEL} {PLUSARGS}\n".format(
                TOPLEVEL=as_tcl_value(
                    f"{self.hdl_toplevel_library}.{self.sim_hdl_toplevel}"
                ),
                EXT_NAME=as_tcl_value(
                    cocotb_tools.config.lib_name_path("vhpi", "riviera").as_posix()
                ),
                EXTRA_ARGS=" ".join(
                    as_tcl_value(v)
                    for v in (
                        self.test_args + self._get_parameter_options(self.parameters)
                    )
                ),
                PLUSARGS=" ".join(as_tcl_value(v) for v in self.plusargs),
            )

            self.env["GPI_EXTRA"] = (
                cocotb_tools.config.lib_name_path("vpi", "riviera").as_posix()
                + ":cocotbvpi_entry_point"
            )
        else:
            do_script += "asim +access +w_nets -interceptcoutput -pli {EXT_NAME} {EXTRA_ARGS} {TOPLEVEL} {PLUSARGS} \n".format(
                TOPLEVEL=as_tcl_value(
                    f"{self.hdl_toplevel_library}.{self.sim_hdl_toplevel}"
                ),
                EXT_NAME=as_tcl_value(
                    cocotb_tools.config.lib_name_path("vpi", "riviera").as_posix()
                ),
                EXTRA_ARGS=" ".join(
                    as_tcl_value(v)
                    for v in (
                        self.test_args + self._get_parameter_options(self.parameters)
                    )
                ),
                PLUSARGS=" ".join(as_tcl_value(v) for v in self.plusargs),
            )

            self.env["GPI_EXTRA"] = (
                cocotb_tools.config.lib_name_path("vhpi", "riviera").as_posix()
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
        # the verilator binary is only needed for building
        return

    def _simulator_in_path_build_only(self) -> None:
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
        self._simulator_in_path_build_only()

        for source in self.sources:
            if not is_verilog_source(source):
                raise ValueError(
                    f"{type(self).__qualname__} only supports Verilog. {str(source)!r} cannot be compiled."
                )
        for arg in self.build_args:
            if type(arg) not in (str, Verilog):
                print(
                    f"WARNING: {type(self).__qualname__} only supports Verilog. build_args {arg!r} will not be applied."
                )

        if self.hdl_toplevel is None:
            raise ValueError(
                f"{type(self).__qualname__} requires the hdl_toplevel parameter to be specified"
            )

        # TODO: set "--debug" if self.verbose
        # TODO: support "--always"

        verilator_cpp = str(
            cocotb_tools.config.share_dir / "lib" / "verilator" / "verilator.cpp"
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
                "--top-module",
                self.hdl_toplevel,
                "--vpi",
                "--public-flat-rw",
                "--prefix",
                "Vtop",
                "-o",
                self.hdl_toplevel,
                "-LDFLAGS",
                f"-Wl,-rpath,{cocotb_tools.config.libs_dir} -L{cocotb_tools.config.libs_dir} -lcocotbvpi_verilator",
            ]
            + (["--trace"] if self.waves else [])
            + [arg for arg in self.build_args if type(arg) in (str, Verilog)]
            + self._get_define_options(self.defines)
            + self._get_include_options(self.includes)
            + self._get_parameter_options(self.parameters)
            + [verilator_cpp]
            + [str(source) for source in self.sources if is_verilog_source(source)]
            + [str(source) for source in self.verilog_sources]
        )

        cmds.append(
            [
                "make",
                "-C",
                str(self.build_dir),
                "-f",
                "Vtop.mk",
                f"VM_TRACE={int(self.waves)}",
            ]
        )

        return cmds

    def _test_command(self) -> List[Command]:
        if self.pre_cmd:
            print("WARNING: pre_cmd is not implemented for Verilator.")

        out_file = self.build_dir / self.sim_hdl_toplevel
        return [
            [str(out_file)]
            + (["--trace"] if self.waves else [])
            + self.test_args
            + self.plusargs
        ]


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

        assert self.hdl_toplevel, "A HDL toplevel is required in all Xcelium compiles."

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

        vhpi_opts = []
        # Xcelium 23.09.004 fixes cocotb issue #1076 as long as the
        # following define is set.
        vhpi_opts.append("-NEW_VHPI_PROPAGATE_DELAY")

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
                cocotb_tools.config.lib_name_path("vpi", "xcelium").as_posix()
                + ":vlog_startup_routines_bootstrap"
            ]
            + vhpi_opts
            + [f"-work {self.hdl_library}"]
            + self.build_args
            + self._get_include_options(self.includes)
            + self._get_define_options(self.defines)
            + self._get_parameter_options(self.parameters)
            + [f"-top {self.hdl_toplevel}"]
            + [
                str(source_file)
                for source_file in (
                    self.sources + self.vhdl_sources + self.verilog_sources
                )
            ]
        ]

        return cmds

    def _test_command(self) -> List[Command]:
        if self.pre_cmd:
            print("WARNING: pre_cmd is not implemented for Xcelium.")

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

        if self.waves:
            input_tcl = [
                f'-input "@database -open cocotb_waves -default" '
                f'-input "@probe -database cocotb_waves -create {xrun_top} -all -depth all" '
                f'-input "@run" '
                f'-input "@exit" '
            ]
        else:
            input_tcl = ["-input", "@run; exit;"]

        vhpi_opts = []
        # Xcelium 23.09.004 fixes cocotb issue #1076 as long as the
        # following define is set.
        vhpi_opts.append("-NEW_VHPI_PROPAGATE_DELAY")

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
            + vhpi_opts
            + verbosity_opts
            + ["-R"]
            + self.test_args
            + self.plusargs
            + ["-gui" if self.gui else ""]
            + input_tcl
        ]
        self.env["GPI_EXTRA"] = (
            cocotb_tools.config.lib_name_path("vhpi", "xcelium").as_posix()
            + ":cocotbvhpi_entry_point"
        )

        return cmds


def get_runner(simulator_name: str) -> Simulator:
    """Return an instance of a runner for *simulator_name*.

    Args:
        simulator_name: Name of simulator to get runner for.

    Raises:
        ValueError: If *simulator_name* is not one of the supported simulators or an alias of one.
    """

    supported_sims: Dict[str, Type[Simulator]] = {
        "icarus": Icarus,
        "questa": Questa,
        "ghdl": Ghdl,
        "riviera": Riviera,
        "verilator": Verilator,
        "xcelium": Xcelium,
        "nvc": Nvc,
        # TODO: "vcs": Vcs,
        # TODO: "activehdl": ActiveHdl,
    }
    try:
        return supported_sims[simulator_name]()
    except KeyError:
        raise ValueError(
            f"Simulator {simulator_name!r} is not in supported list: {', '.join(supported_sims)}"
        ) from None
