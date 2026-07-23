# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Compatibility layer between cocotb and pytest. Converts cocotb decorators to pytest markers."""

from __future__ import annotations

from typing import Any

from pytest import Class, Collector, Config, Item, Mark, Module, hookimpl, mark

from cocotb._decorators import Test, TestGenerator


class Compat:
    """A compatibility layer between cocotb and pytest.

    This class is used as an internal sub-plugin for the main cocotb pytest plugin.
    """

    def __init__(self, config: Config) -> None:
        """Create a new instance of the compatibility layer between cocotb and pytest.

        Args:
            config: The pytest configuration object.
        """
        self.python: Any = config.pluginmanager.getplugin("python")

    @hookimpl(tryfirst=True)
    def pytest_pycollect_makeitem(
        self, collector: Module | Class, name: str, obj: object
    ) -> None | Item | Collector | list[Item | Collector]:
        """Identify cocotb tests during pytest collection and apply markers.

        Args:
            collector: The Python module or class collector.
            name: The name of the Python object in the collector.
            obj: The Python object (e.g., a test function).

        Returns:
            :data:`None` to delegate the creation of the test function from the collected ``obj`` to other plugins.
            A non-:data:`None` value if the collected ``obj`` is a pytest item (test function) or another pytest collector.
        """
        if isinstance(obj, (Test, TestGenerator)):
            # Convert @cocotb.test decorator to @pytest.mark.cocotb_* markers and @cocotb.parametrize decorator to @pytest.mark.parametrize markers
            obj = cocotb_decorators_to_pytest_marks(obj)

            # This is needed by the pytest code inspection mechanism. Otherwise pytest will raise an error when generating parametrized tests
            setattr(collector.obj, name, obj)

            # Delegate creation of test functions to the pytest built-in 'python' plugin
            return self.python.pytest_pycollect_makeitem(
                collector=collector, name=name, obj=obj
            )

        return None


def cocotb_decorators_to_pytest_marks(test: Test | TestGenerator) -> object:
    """Convert a cocotb-decorated test function/generator to equivalent pytest markers.

    This function extracts parameters, timeouts, skip conditions, and expected failures
    from cocotb test decorators and applies them as pytest marks on the underlying function.

    Example:
        Given a test function decorated with ``@cocotb.test(skip=True)``, this function
        will attach the ``pytest.mark.skip`` marker to the test function.

    Args:
        test: The cocotb test or test generator object.

    Returns:
        The unwrapped test function with the applied pytest markers.
    """
    markers: list[Mark] = []

    # Replace @cocotb.parametrize(...) decorator with equivalent @pytest.mark.parametrize(...) markers
    # @cocotb.parametrize(x=[1, 2], y=[3, 4])
    # vvv
    # @pytest.parametrize("x", [1, 2])
    # @pytest.parametrize("y", [3, 4])
    if isinstance(test, TestGenerator):
        for names, values in test.options:
            if isinstance(names, str):
                markers.append(mark.parametrize(names, values).mark)
            else:
                markers.append(mark.parametrize(",".join(names), values).mark)

    if test.stage:
        # Supported by an external plugin that must be installed independently: pytest-order
        markers.append(mark.order(test.stage).mark)

    if test.skip:
        markers.append(mark.skip(reason="skipping cocotb test").mark)

    if test.expect_fail or test.expect_error:
        markers.append(
            mark.xfail(
                raises=tuple(test.expect_error) if test.expect_error else None,  # type: ignore[arg-type]
                strict=True,
            ).mark
        )

    if test.timeout:
        markers.append(
            mark.cocotb_timeout(duration=test.timeout[0], unit=test.timeout[1]).mark
        )

    obj: object = test.func

    # Add existing pytest markers extracted from used cocotb decorator
    # @pytest.mark.*
    # @cocotb.test
    markers.extend(getattr(test, "pytestmark", ()))

    # Add existing pytest markers extracted from defined test function
    # @pytest.mark.*
    # async def test_dut_feature_1(dut) -> None:
    markers.extend(getattr(obj, "pytestmark", ()))

    # Add all combined pytest markers to object (test function)
    setattr(obj, "pytestmark", markers)

    # __test__ will tell pytest to treat this object as a test item
    setattr(obj, "__test__", True)

    return obj
