# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Collection of fixture decorators."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, Callable, Literal, overload

from _pytest.fixtures import FixtureFunctionDefinition, FixtureFunctionMarker
from pytest import Config

ScopeName = Literal["session", "package", "module", "class", "function"]
"""Scope name of pytest fixture."""


class _DutFixture(FixtureFunctionMarker):  # type: ignore # inherit from final class. We only override class method
    def __call__(self, function: Callable[..., object]) -> FixtureFunctionDefinition:
        # Tell plugin that this fixture function is used as DUT fixture
        setattr(function, "__cocotb_dut_fixture__", True)

        return super().__call__(function)


@overload
def dut(
    fixture_function: Callable[..., object],
    *,
    scope: ScopeName | Callable[[str, Config], ScopeName] = ...,
    params: Iterable[object] | None = ...,
    autouse: bool = ...,
    ids: Sequence[object | None] | Callable[[Any], object | None] | None = ...,
    name: str | None = ...,
) -> object: ...


@overload
def dut(
    fixture_function: None = ...,
    *,
    scope: ScopeName | Callable[[str, Config], ScopeName] = ...,
    params: Iterable[object] | None = ...,
    autouse: bool = ...,
    ids: Sequence[object | None] | Callable[[Any], object | None] | None = ...,
    name: str | None = None,
) -> object: ...


def dut(
    fixture_function: Callable[..., object] | None = None,
    *,
    scope: ScopeName | Callable[[str, Config], ScopeName] = "function",
    params: Iterable[object] | None = None,
    autouse: bool = False,
    ids: Sequence[object | None] | Callable[[Any], object | None] | None = None,
    name: str | None = None,
) -> object:
    """Decorator to mark function as a Design-Under-Test (DUT) fixture.

    This decorator can be used, with or without parameters, to define a fixture function.

    Decorator is an extended version of the :deco:`pytest.fixture` with the same arguments and behavior.
    It tells plugin that decorated function is used to build HDL design during the test ``setup`` stage.
    And returned result from fixture can be used by plugin to run HDL simulation with built HDL design.

    Args:
        scope:
            The scope for which this fixture is shared; one of ``"function"`` (default), ``"class"``, ``"module"``, ``"package"`` or ``"session"``.
            This parameter may also be a callable which receives ``(fixture_name, config)`` as parameters,
            and must return a ``str`` with one of the values mentioned above.

        params:
            An optional list of parameters which will cause multiple invocations of the fixture function and all of the tests using it.
            The current parameter is available in ``request.param``.

        autouse:
            If data:`True`, the fixture func is activated for all tests that can see it.
            If data:`False` (the default), an explicit reference is needed to activate the fixture.

        ids:
            Sequence of ids each corresponding to the params so that they are part of the test id.
            If no ids are provided they will be generated automatically from the params.

        name:
            The name of the fixture. This defaults to the name of the decorated function.
            If a fixture is used in the same module in which it is defined,
            the function name of the fixture will be shadowed by the function arg that requests the fixture;
            one way to resolve this is to name the decorated function ``fixture_<fixturename>`` and then use ``@pytest.fixture(name='<fixturename>')``.

    Returns:
        Decorated function marked as a Design-Under-Test (DUT) fixture that can be used by plugin.
    """
    dut_fixture = _DutFixture(
        scope=scope,
        params=tuple(params) if params is not None else None,
        autouse=autouse,
        ids=None if ids is None else ids if callable(ids) else tuple(ids),
        name=name,
        _ispytest=True,
    )

    return dut_fixture(fixture_function) if fixture_function else dut_fixture
