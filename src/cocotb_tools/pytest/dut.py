# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Design Under Test (DUT) representation and configuration management."""

from __future__ import annotations

from argparse import Namespace
from collections.abc import Sequence
from hashlib import md5
from pathlib import Path
from typing import Any, Callable

from pytest import Config, FixtureRequest, Mark, Module

from cocotb_tools.pytest._simulator import (
    detect_language,
    detect_languages,
    find_simulator,
    get_supported_languages,
)
from cocotb_tools.runner import (
    VHDL,
    PathLike,
    VerilatorControlFile,
    Verilog,
)

#: Exclude these attributes when generating unique DUT identifier
_EXCLUDE_FROM_ID: tuple[str, ...] = (
    "test_modules",
    "random_seed",
    "build_dir",
    "work_dir",
    "id",
)


class Dut:
    """Representation of a Design Under Test (DUT).

    This class holds the configuration and state required to compile, elaborate,
    and run an HDL module using an HDL simulator and cocotb tests.

    Example:
        To customize a DUT in a test module or fixture:

        .. code-block:: python

            import pytest
            from pathlib import Path
            from cocotb_tools.pytest.dut import Dut

            DIR = Path(__file__).parent.resolve()


            @pytest.fixture
            def my_module(dut: Dut) -> Dut:
                dut.sources += [DIR / "rtl" / "my_design.v"]
                dut["WIDTH"] = 16

                return dut
    """

    def __init__(self, request: FixtureRequest) -> None:
        """Initialize a new instance of DUT (Design Under Test).

        Args:
            request: The pytest fixture request object containing configuration and context.
        """
        config: Config = request.config
        option: Namespace = config.option

        self._run: Callable[..., None] = request.config.hook.pytest_cocotb_dut_run
        self._simulator: str | None
        self.simulator = option.cocotb_simulator

        self.suffix: str = ""
        """The suffix name that will be added to name of this DUT instance."""

        # Build options
        self._defines: dict[str, object]
        self.defines = option.cocotb_defines

        self._parameters: dict[str, object]
        self.parameters = option.cocotb_parameters

        self._timescale: tuple[str, str] | None
        self.timescale = option.cocotb_timescale

        self.library: str = option.cocotb_library
        """The library name to compile into."""

        self.sources: list[PathLike | VHDL | Verilog | VerilatorControlFile] = (
            option.cocotb_sources.copy()
        )
        """Language-agnostic list of source files to build."""

        self.includes: list[PathLike] = option.cocotb_includes.copy()
        """Verilog include directories."""

        self.build_args: list[str | VHDL | Verilog] = option.cocotb_build_args.copy()
        """A list of extra build arguments for the simulator."""

        self._toplevel: str | None = None
        """Name of the HDL toplevel module."""

        self.always: bool = option.cocotb_always
        """Always run the build step."""

        self.clean: bool = option.cocotb_clean
        """Delete *build_dir* before building."""

        self.verbose: bool = option.cocotb_verbose
        """Enable verbose messages."""

        self.waves: bool = option.cocotb_waves
        """Record signal traces."""

        self.build_dir: PathLike = option.cocotb_build_dir
        """Directory to run the build step in."""

        # Test options
        self._env: dict[str, object]
        self.env = option.cocotb_env

        self.test_modules: list[str] = []
        """The name of the Python module(s) with cocotb test(s) to run."""

        self.toplevel_library: str = option.cocotb_toplevel_library
        """The library name for HDL toplevel module."""

        self._toplevel_lang: str = option.cocotb_toplevel_lang
        """Language of the HDL toplevel module."""

        self.gpi_interfaces: list[str] = option.cocotb_gpi_interfaces.copy()
        """List of GPI interfaces to use, with the first one being the entry point."""

        self._random_seed: int = option.cocotb_random_seed
        """A specific random seed to use."""

        self.elab_args: list[str] = option.cocotb_elab_args.copy()
        """A list of extra elaboration arguments for the simulator."""

        self.sim_args: list[str] = option.cocotb_sim_args.copy()
        """A list of extra simulation arguments for the simulator."""

        self.plusargs: list[str] = option.cocotb_plusargs.copy()
        """'plusargs' to set for the simulator."""

        self.gui: bool = option.cocotb_gui
        """Run with simulator GUI."""

        self.pre_cmd: list[str] = option.cocotb_pre_cmd.copy()
        """Commands to run before simulation begins. Typically Tcl commands for simulators that support them."""

        self.test_filter: str = option.cocotb_test_filter
        """Regular expression which matches test names."""

        self._apply_markers(request.node)

        if not Path(self.build_dir).is_absolute():
            self.build_dir = request.config.invocation_params.dir / self.build_dir

        if not self.test_modules:
            module: Module | None = request.node.getparent(Module)

            if module:
                self.test_modules.append(module.getmodpath(includemodule=True))

    @classmethod
    def create(cls, request: FixtureRequest) -> Dut:
        """Create a new instance of DUT (Design Under Test) via the pytest hooks.

        Args:
            request: The pytest fixture request.

        Returns:
            The created Dut instance.
        """
        return request.config.hook.pytest_cocotb_dut_create(request=request)

    def run(self) -> None:
        """Compile, elaborate, and run the HDL module using the HDL simulator and cocotb tests."""
        __tracebackhide__ = True  # Hide the traceback when using PyTest.

        # Propagate pytest keywords that can be used with the pytest '-k <expr>' argument to simulation process
        self.env["COCOTB_PYTEST_KEYWORDS"] = ",".join(
            (self.toplevel_library, str(self.toplevel), self.name)
        )

        self._run(dut=self)

    @property
    def name(self) -> str:
        """Return the name of the DUT instance.

        The name is formatted as ``<toplevel_library>.<toplevel>[<parameters>]``.
        """
        name: str = f"{self.toplevel_library}.{self.toplevel}"

        if self.parameters:
            name += "[" + ",".join(f"{k}={v}" for k, v in self.parameters.items()) + "]"

        if self.suffix:
            name += f".{self.suffix}"

        return name

    @property
    def simulator(self) -> str | None:
        """The name of the HDL simulator."""
        if self._simulator and self._simulator != "auto":
            return self._simulator

        return find_simulator(
            languages=detect_languages(self.sources) or self._toplevel_lang
        )

    @simulator.setter
    def simulator(self, simulator: str | None) -> None:
        self._simulator = simulator

    @property
    def toplevel(self) -> str | None:
        """The name of the HDL toplevel module.

        If the toplevel module name is not set explicitly, it is inferred from:

        * The filename of the last source file in the :attr:`cocotb_tools.pytest.dut.Dut.sources` attribute, excluding the file extension.
        * The name of the first Python test module in the :attr:`cocotb_tools.pytest.dut.Dut.test_modules` attribute, excluding the standard pytest ``test_`` prefix or ``_test`` suffix.

        Returns:
            The toplevel module name, or :data:`None` if it cannot be determined.
        """
        if self._toplevel:
            return self._toplevel

        if self.sources:
            source = self.sources[-1]

            if isinstance(source, (Verilog, VHDL, VerilatorControlFile)):
                source = source.value

            if not isinstance(source, Path):
                source = Path(str(source))

            # In case when filename will contain more dots... Example: <name>.e.vhd
            return source.name.partition(".")[0]

        if not self.test_modules:
            return None

        # Pick the first test module
        # ["tests.test_dut", "tests.test_extra"] -> test_dut
        test_module: str = self.test_modules[0].rpartition(".")[2]

        if test_module.startswith("test_"):
            return test_module.removeprefix("test_")

        if test_module.endswith("_test"):
            return test_module.removesuffix("_test")

        return test_module

    @toplevel.setter
    def toplevel(self, toplevel: str | None) -> None:
        self._toplevel = toplevel

    @property
    def toplevel_lang(self) -> str | None:
        """The language of the HDL toplevel module.

        If the language is not set explicitly, it is inferred from:

        * The file type or file extension of the last added source file in the :attr:`cocotb_tools.pytest.dut.Dut.sources` attribute.

        Returns:
            The language string, or :data:`None` if it cannot be determined.
        """
        if self._toplevel_lang and self._toplevel_lang != "auto":
            return self._toplevel_lang

        if self.sources:
            return detect_language(self.sources[-1])

        supported_languages: list[str] = get_supported_languages(self.simulator)

        # Pick the first supported language
        return supported_languages[0] if supported_languages else None

    @toplevel_lang.setter
    def toplevel_lang(self, toplevel_lang: str) -> None:
        self._toplevel_lang = toplevel_lang

    @property
    def timescale(self) -> tuple[str, str] | None:
        """A tuple containing the time unit and time precision for the simulation."""
        return self._timescale

    @timescale.setter
    def timescale(self, timescale: str | tuple[str, str] | None) -> None:
        time_unit: str = ""
        time_precision: str = ""

        if isinstance(timescale, str):
            time_unit, _, time_precision = timescale.partition("/")

        elif isinstance(timescale, tuple) and len(timescale) == 2:
            time_unit, time_precision = timescale

        time_unit = time_unit.strip()
        time_precision = time_precision.strip()

        self._timescale = (
            (time_unit, time_precision or time_unit) if time_unit else None
        )

    @property
    def random_seed(self) -> int:
        """A specific random seed to use."""
        return self._random_seed

    @property
    def parameters(self) -> dict[str, object]:
        """A dictionary of Verilog parameters or VHDL generics."""
        return self._parameters

    @parameters.setter
    def parameters(self, parameters: Sequence[str] | dict[str, object]) -> None:
        if isinstance(parameters, Sequence):
            self._parameters = {}
            self._update_dict_with_list(self._parameters, parameters)
        else:
            self._parameters = parameters

    @property
    def defines(self) -> dict[str, object]:
        """A dictionary of preprocessor defines to set."""
        return self._defines

    @defines.setter
    def defines(self, defines: Sequence[str] | dict[str, object]) -> None:
        if isinstance(defines, Sequence):
            self._defines = {}
            self._update_dict_with_list(self._defines, defines)
        else:
            self._defines = defines

    @property
    def env(self) -> dict[str, object]:
        """A dictionary of extra environment variables to set for the simulation."""
        return self._env

    @env.setter
    def env(self, env: Sequence[str] | dict[str, object]) -> None:
        if isinstance(env, Sequence):
            self._env = {}
            self._update_dict_with_list(self._env, env)
        else:
            self._env = env

    @property
    def id(self) -> str:
        """A unique DUT identifier based on the current build and run configuration of the Dut instance.

        It is used to group cocotb tests that run sequentially within the same HDL simulation process.
        This identifier is also used as a group name when distributing tests across multiple CPUs
        using the `pytest-xdist`_ plugin.

        .. _pytest-xdist: https://pytest-xdist.readthedocs.io/en/stable/distribution.html#running-tests-across-multiple-cpus
        """
        hashed = md5()

        for name in dir(self):
            if not name.startswith("_") and name not in _EXCLUDE_FROM_ID:
                attr = getattr(self, name)

                if not callable(attr):
                    hashed.update(str(attr).encode("utf-8"))

        return hashed.hexdigest()

    @property
    def work_dir(self) -> Path:
        """The absolute path to the unique work directory from which the DUT is compiled, elaborated, and run.

        Schema:

        .. code:: text

           <dut.build_dir>/<dut.toplevel_library>/<dut.toplevel>/<dut.parameters>/<dut.id>

        Example:

        .. code:: text

           build_sim/top/alu/WIDTH_8/d75117a510e1020e864f36822f96eeb8b9427534
        """
        parameters: str = (
            "_".join(f"{k}_{v}" for k, v in self.parameters.items()).strip("_")
            or "default"
        )

        return (
            Path(self.build_dir).resolve()
            / self.toplevel_library
            / str(self.toplevel)
            / parameters
            / self.id
        )

    def __setitem__(self, key: str, value: object) -> None:
        """Set an HDL parameter or VHDL generic value in the design configuration."""
        self.parameters[key] = value

    def __getitem__(self, key: str) -> object:
        """Get the configured value of an HDL parameter or VHDL generic."""
        return self.parameters[key]

    def _apply_markers(self, node: Any) -> None:
        """Apply all cocotb markers starting from the root (session) to the leaf (test function).

        * Markers with positional arguments are extending targeted attribute.
        * Markers with named arguments are updating targeted attribute.

        Args:
            node: The pytest node (session, package, module, class, function, ...).
        """
        for marker in reversed(list(node.iter_markers())):
            self._apply_marker(marker)

    def _apply_marker(self, marker: Mark) -> None:
        """Apply cocotb marker directly on DUT instance."""
        name: str = marker.name

        if not name.startswith("cocotb_"):
            return

        name = name.removeprefix("cocotb_")

        if not name or name[0] == "_" or not hasattr(self, name):
            return

        attr: Any = getattr(self, name)

        if isinstance(attr, dict):
            attr.update(marker.kwargs)
            self._update_dict_with_list(attr, marker.args)
        elif isinstance(attr, list):
            attr.extend(marker.args)
        elif isinstance(attr, bool):
            setattr(self, name, bool(marker.args[0]) if marker.args else True)
        elif marker.args:
            setattr(self, name, marker.args[0])

    def _update_dict_with_list(
        self, items: dict[str, object], values: Sequence[str]
    ) -> None:
        for value in values:
            key, _, item = value.partition("=")
            items[key] = item
