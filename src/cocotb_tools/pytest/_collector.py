# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Module collects cocotb tests in non-simulation environment and based on them, it creates simulation items.

During tests collection, it creates hierarchy between discovered DUTs, test modules and cocotb tests::

   <Cocotb>
     <Dut library.top[PARAM1=8,PARAM2=16]>
       <Function simulation>
       <TestModule tests.test_module_1>
         <Function test_dut_feature_1>
         <Function test_dut_feature_2>
       <TestModule tests.test_module_2>
         <Function test_dut_feature_3[2-4]>
         <Function test_dut_feature_3[4-8]>

* The ``Cocotb`` node represents the root of all collected DUTs, test modules and cocotb tests
* The ``Dut`` node represents the Design Under Test based on collected :class:`cocotb_tools.pytest.dut.Dut` fixture
* The ``simulation`` item represents a test function that will compile, elaborate and run the HDL module with the HDL simulation and cocotb tests
* The ``TestModule`` node represents collection of Python modules with cocotb tests
* The ``Function`` item represents  a single test function (cocotb test or simulation process)
"""

from __future__ import annotations

from collections.abc import Generator, Iterable
from inspect import iscoroutinefunction
from typing import Any, get_args, get_origin, get_type_hints

from pytest import (
    Class,
    Collector,
    Config,
    ExceptionInfo,
    FixtureDef,
    Function,
    Item,
    Module,
    Session,
    hookimpl,
)

from cocotb_tools.pytest._utils import to_list
from cocotb_tools.pytest.dut import Dut


class Node(Collector):
    """Represents a cocotb node (build, simulation, test module, test)."""

    def collect(self) -> Iterable[Item | Collector]:  # pragma: no cover
        """This class works as a node not as a collector. Suppressing raised error about not implemented method."""
        return []


class Simulation(Item):
    """Represents a simulation runtime process.

    This item corresponds to the actual execution of an HDL simulator.
    """

    def __init__(self, *args: Any, dut: Dut, **kwargs: Any) -> None:
        """Create a new instance of a simulation item to be invoked by pytest."""
        super().__init__(*args, **kwargs)

        self.add_marker("cocotb")
        self.add_marker("cocotb_simulation")
        self.dut: Dut = dut

    def runtest(self) -> None:
        """Compile, elaborate, and run the HDL module with the HDL simulator and cocotb tests."""
        __tracebackhide__ = True  # Hide the traceback when using PyTest.

        self.dut.run()

    def repr_failure(
        self, excinfo: ExceptionInfo[BaseException], style: Any = "short"
    ) -> Any:
        """Return a representation of a test failure.

        Args:
            excinfo: Exception information for the failure.
            style: Set style for returned representation.

        Returns:
            Representation of the failure.
        """
        # Remove all entries from the traceback with the __tracebackhide__ variable set to True and with the pytest itself
        excinfo.traceback = excinfo.traceback.filter(excinfo).filter(
            remove_pytest_traceback
        )

        return super().repr_failure(excinfo, style=style)

    def __repr__(self) -> str:
        """The representation name of the simulation process."""
        return f"<Function {self.name}>"


class TestModule(Module):
    """Represents a collection of cocotb tests inside a Python module."""

    def collect_dut_item(self, dut: Dut, item: Item) -> Iterable[Item]:
        """Collect a cocotb test item and group it under this test module."""
        item.parent = self
        item.add_marker("cocotb")
        item.add_marker("cocotb_test")
        item.extra_keyword_matches.add(dut.name)

        if self.config.option.collectonly:
            yield item


class Build(Node):
    """Represents a simulation build step."""

    def __init__(self, *args: Any, dut: Dut, **kwargs: Any) -> None:
        """Create a new build collector instance."""
        super().__init__(*args, **kwargs)

        self.simulation: Simulation = Simulation.from_parent(
            self, name="simulation", dut=dut
        )
        self.test_modules: dict[str, TestModule] = {}

    def collect_dut_item(self, dut: Dut, item: Item) -> Iterable[Item]:
        """Collect a cocotb test item and group it under this build."""
        module: Module | None = item.getparent(Module)

        if module:
            name: str = module.getmodpath(includemodule=True)
            test_module: TestModule | None = self.test_modules.get(name)

            if not test_module:
                test_module = TestModule.from_parent(self, name=name, path=module.path)
                self.test_modules[name] = test_module

                if name not in self.simulation.dut.test_modules:
                    self.simulation.dut.test_modules.append(name)

            yield from test_module.collect_dut_item(dut, item)

    def __repr__(self) -> str:
        """The representation name of the simulation build."""
        return f"<Dut {self.name}>"


class Cocotb(Node):
    """Represents collection of simulation builds, test modules and cocotb tests."""

    def __init__(self, **kwargs: Any) -> None:
        """Create a new Cocotb collector instance."""
        super().__init__(name="cocotb", **kwargs)

        self.builds: dict[str, Build] = {}
        """A mapping of unique simulation builds, using the :attr:`cocotb_tools.pytest.dut.Dut.id` as the key."""

        self._build_indexes: dict[str, int] = {}
        """Used to generate an unique name of a simulation build where the :attr:`cocotb_tools.pytest.dut.Dut.name` is the same."""

    @hookimpl(wrapper=True)
    def pytest_pycollect_makeitem(
        self, collector: Module | Class, name: str, obj: object
    ) -> Generator[
        None,
        None | Item | Collector | list[Item | Collector],
        None | Item | Collector | list[Item | Collector],
    ]:
        """Intercept item creation during collection to process cocotb tests.

        Args:
            collector: The Python module or class collector.
            name: The name of the Python object in the collector.
            obj: The Python object (e.g., a test function).

        Yields:
            The collected simulation item or cocotb test.
        """
        items: None | Item | Collector | list[Item | Collector] = yield

        if items is not None:
            items = list(self.collect_items(to_list(items)))

        return items

    @hookimpl(tryfirst=True)
    def pytest_collection_modifyitems(
        self, session: Session, config: Config, items: list[Item]
    ) -> None:
        """Called after collection has been performed. May filter or re-order the items in-place.

        Args:
            session: The pytest session object.
            config: The pytest config object.
            items: List of item objects.
        """
        if config.option.collectonly:
            # Show all simulation builds and cocotb tests as last when listing collected items
            items.sort(key=is_build)

    def collect_items(
        self, items: Iterable[Item | Collector]
    ) -> Generator[Item | Collector, None, None]:
        """Filter and collect cocotb test functions, resolving their DUT fixtures."""
        for item in items:
            if isinstance(item, Function) and iscoroutinefunction(item.function):
                for dut in get_dut_fixtures(item):
                    yield from self.collect_dut_item(dut, item)
            else:
                yield item

    def collect_dut_item(
        self, dut: Dut, item: Item
    ) -> Generator[Item | Collector, None, None]:
        """Collect simulation builds and tests for a specific DUT fixture."""
        build_id: str = dut.id
        build: Build | None = self.builds.get(build_id)

        if not build:
            build = Build.from_parent(self, name=self.generate_build_name(dut), dut=dut)
            self.builds[build_id] = build

            if not self.config.option.cocotb_with_user_runners:
                yield build.simulation

        yield from build.collect_dut_item(dut, item)

    def generate_build_name(self, dut: Dut) -> str:
        """Generate an unique and human-friendly name for the simulation build."""
        name: str = dut.name

        index: int = self._build_indexes.get(name, 0)
        self._build_indexes[name] = index + 1

        return f"{name}.{index}" if index else name

    def __repr__(self) -> str:
        """The representation name of the cocotb collector."""
        return "<Cocotb>"


def is_build(item: Item) -> bool:
    """Check if a provided item is a simulation build."""
    return item.getparent(Build) is not None


def is_dut_type(obj: object) -> bool:
    """Check if the provided object is a subclass of the :class:`cocotb_tools.pytest.dut.Dut` class."""
    return isinstance(obj, type) and issubclass(obj, Dut)


def is_dut_fixture(fixturedef: FixtureDef) -> bool:
    """Check if the return type annotation of the fixture is a subclass of the :class:`cocotb_tools.pytest.dut.Dut` class.

    This function inspects the fixture's return type hints, handling single type hints as well as Union or UnionType annotations.
    """
    return_annotation = get_type_hints(fixturedef.func).get("return")

    if not return_annotation:
        return False

    if get_origin(return_annotation):
        # Check return annotation: -> Dut | ...:
        # Check return annotation: -> Union[Dut, ...]:
        # Check return annotation: -> Optional[Dut]:
        return any(map(is_dut_type, get_args(return_annotation)))

    # Check return annotation: -> Dut:
    return is_dut_type(return_annotation)


def get_dut_fixture_names(item: Function) -> list[str]:
    """Get the names of fixtures that return a :class:`cocotb_tools.pytest.dut.Dut` instance.

    Args:
        item: The pytest item function (test function).

    Returns:
        A list of DUT fixture names.
    """
    names: list[str] = []

    for argname, fixturedefs in item._fixtureinfo.name2fixturedefs.items():
        if argname == "dut" or fixturedefs and is_dut_fixture(fixturedefs[-1]):
            names.append(argname)

    return names


def get_dut_fixtures(item: Function) -> Generator[Dut, None, None]:
    """Generate active :class:`cocotb_tools.pytest.dut.Dut` fixture instances for the test function.

    Args:
        item: The pytest item function (test function).

    Yields:
        An instance of the DUT fixture.
    """
    # Cache original fixture names from the pytest item to restore them later
    fixturenames = item.fixturenames

    # Fixture values
    values: Iterable[object]

    # Request only DUT fixtures
    item.fixturenames = get_dut_fixture_names(item) or ["dut"]

    try:
        # The setup will fill the pytest item with fixtures based on the pytest item fixture names
        item.session._setupstate.setup(item)
    finally:
        # Restore the original list of fixture names
        values = item.funcargs.values()
        item.fixturenames = fixturenames
        item.funcargs = {}

    # Item should be teardown after setup
    item.session._setupstate.teardown_exact(None)

    # Get list of requested fixture instances
    for dut in values:
        if isinstance(dut, Dut):
            yield dut


def remove_pytest_traceback(entry: Any) -> bool:
    """Remove a pytest traceback entry from an exception traceback."""
    return entry.path.parent.name not in ("_pytest", "pluggy")
