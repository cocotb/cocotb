# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import inspect
import sys
from collections.abc import Coroutine, Iterable, Mapping, Sequence
from enum import Enum
from functools import cached_property
from itertools import product
from typing import Any, Callable, cast, overload

from cocotb._base_triggers import Trigger
from cocotb.simtime import TimeUnit

if sys.version_info >= (3, 10):
    from typing import TypeAlias


class Test:
    """A cocotb test in a regression.

    Args:
        func:
            The test function object.

        args:
            Positional arguments to pass to the test function.

        kwargs:
            Keyword arguments to pass to the test function.

        name:
            The name of the test function.

        module:
            The name of the module containing the test function.

        doc:
            The docstring for the test.

        timeout:
            Simulation time duration before the test is forced to fail with a :exc:`~cocotb.triggers.SimTimeoutError`.
            A tuple of the timeout value and unit.
            Accepts any unit that :class:`~cocotb.triggers.Timer` does.

        expect_fail:
            If ``True`` and the test fails a functional check via an :keyword:`assert` statement, :func:`pytest.raises`,
            :func:`pytest.warns`, or :func:`pytest.deprecated_call`, the test is considered to have passed.
            If ``True`` and the test passes successfully, the test is considered to have failed.

        expect_error:
            Mark the result as a pass only if one of the given exception types is raised in the test.

        skip:
            Don't execute this test as part of the regression.
            The test can still be run manually by setting :envvar:`COCOTB_TESTCASE`.

        stage:
            Order tests logically into stages.
            Tests from earlier stages are run before tests from later stages.
    """

    # TODO Replace with dataclass in Python 3.7+

    def __init__(
        self,
        *,
        func: Callable[..., Coroutine[Trigger, None, None]],
        args: Sequence[Any],
        kwargs: Mapping[str, Any],
        name: str,
        module: str,
        doc: str | None,
        timeout: tuple[float, TimeUnit] | None,
        expect_fail: bool,
        expect_error: tuple[type[BaseException], ...],
        skip: bool,
        stage: int,
    ) -> None:
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.name = name
        self.module = module
        self.doc = doc
        self.timeout = timeout
        self.expect_fail = expect_fail
        self.expect_error = expect_error
        self.skip = skip
        self.stage = stage

    @cached_property
    def fullname(self) -> str:
        return f"{self.module}.{self.name}"


TestFuncType: TypeAlias = Callable[..., Coroutine[Trigger, None, None]]


class TestGenerator:
    def __init__(
        self,
        func: TestFuncType,
    ) -> None:
        self.func: TestFuncType = func
        self.timeout: tuple[float, TimeUnit] | None = None
        self.expect_fail: bool = False
        self.expect_error: set[type[BaseException]] = set()
        self.skip = False
        self.stage = 0
        self.name = self.func.__qualname__
        self.module = self.func.__module__
        self.doc = self.func.__doc__
        if self.doc is not None:
            # cleanup docstring using `trim` function from PEP257
            self.doc = inspect.cleandoc(self.doc)
        self.options: list[
            tuple[str, Sequence[object]]
            | tuple[Sequence[str], Sequence[Sequence[object]]]
        ] = []

    def generate_tests(self) -> Iterable[Test]:
        option_reprs: dict[str, list[str]] = {}

        for name, values in self.options:
            if isinstance(name, str):
                option_reprs[name] = _reprs(values)
            else:
                # transform to Dict[name, values]
                transformed: dict[str, list[object]] = {}
                for nam_idx, nam in enumerate(name):
                    transformed[nam] = []
                    for value_array in cast("Sequence[Sequence[object]]", values):
                        value = value_array[nam_idx]
                        transformed[nam].append(value)
                for n, vs in transformed.items():
                    option_reprs[n] = _reprs(vs)

        # this value is a list of ranges of the same length as each set of values in self.options for passing to itertools.product
        option_indexes = [range(len(option[1])) for option in self.options]

        # go through the cartesian product of all values of all options
        for selected_options in product(*option_indexes):
            test_kwargs: dict[str, object] = {}
            test_name_pieces: list[str] = [self.name]
            for option_idx, select_idx in enumerate(selected_options):
                option_name, option_values = self.options[option_idx]
                selected_value = option_values[select_idx]

                if isinstance(option_name, str):
                    # single params per option
                    selected_value = cast("Sequence[object]", selected_value)
                    test_kwargs[option_name] = selected_value
                    test_name_pieces.append(
                        f"/{option_name}={option_reprs[option_name][select_idx]}"
                    )
                else:
                    # multiple params per option
                    selected_value = cast("Sequence[object]", selected_value)
                    for n, v in zip(option_name, selected_value):
                        test_kwargs[n] = v
                        test_name_pieces.append(f"/{n}={option_reprs[n][select_idx]}")

            parametrized_test_name = "".join(test_name_pieces)

            yield Test(
                func=self.func,
                args=(),
                kwargs=test_kwargs,
                name=parametrized_test_name,
                module=self.module,
                doc=self.doc,
                timeout=self.timeout,
                expect_fail=self.expect_fail,
                expect_error=tuple(self.expect_error),
                skip=self.skip,
                stage=self.stage,
            )


def _reprs(values: Sequence[object]) -> list[str]:
    result: list[str] = []
    for value in values:
        value_repr = _repr(value)
        if value_repr is None:
            # non-representable value in option, so default to index strings and give up
            return [str(i) for i in range(len(values))]
        else:
            result.append(value_repr)
    return result


def _repr(v: object) -> str | None:
    if isinstance(v, Enum):
        return v.name
    elif isinstance(v, str):
        if len(v) <= 10 and v.isidentifier():
            return v
        else:
            return None
    elif isinstance(v, (int, float, bool, type(None))):
        return repr(v)
    elif isinstance(v, type):
        return v.__qualname__
    elif hasattr(v, "__qualname__"):
        return v.__qualname__
    else:
        return None


@overload
def test(obj: TestFuncType | TestGenerator) -> TestGenerator: ...


@overload
def test(
    *,
    timeout_time: float | None = None,
    timeout_unit: TimeUnit = "step",
    expect_fail: bool = False,
    expect_error: type[BaseException] | tuple[type[BaseException], ...] = (),
    skip: bool = False,
    stage: int = 0,
    name: str | None = None,
) -> Callable[[TestFuncType | TestGenerator], TestGenerator]: ...


def test(
    obj: TestFuncType | TestGenerator | None = None,
    *,
    timeout_time: float | None = None,
    timeout_unit: TimeUnit = "step",
    expect_fail: bool | None = None,
    expect_error: type[BaseException] | tuple[type[BaseException], ...] | None = None,
    skip: bool | None = None,
    stage: int | None = None,
    name: str | None = None,
) -> TestGenerator | Callable[[TestFuncType | TestGenerator], TestGenerator]:
    r"""
    Decorator to register a Callable which returns a Coroutine as a test.

    The test decorator provides a test timeout, and allows us to mark tests as skipped or expecting errors or failures.
    Tests are evaluated in the order they are defined in a test module.

    Usage:
        .. code-block:: python

            @cocotb.test(timeout_time=10, timeout_unit="ms")
            async def test_thing(dut): ...

    Args:
        timeout_time:
            Simulation time duration before timeout occurs.

            .. versionadded:: 1.3

            .. note::
                Test timeout is intended for protection against deadlock.
                Users should use :class:`~cocotb.triggers.with_timeout` if they require a
                more general-purpose timeout mechanism.

        timeout_unit:
            Units of timeout_time, accepts any units that :class:`~cocotb.triggers.Timer` does.

            .. versionadded:: 1.3

            .. versionchanged:: 2.0
                Passing ``None`` as the *timeout_unit* argument was removed, use ``'step'`` instead.

        expect_fail:
            If ``True`` and the test fails a functional check via an :keyword:`assert` statement, :class:`pytest.raises`,
            :class:`pytest.warns`, or :class:`pytest.deprecated_call` the test is considered to have passed.
            If ``True`` and the test passes successfully, the test is considered to have failed.

        expect_error:
            Mark the result as a pass only if one of the exception types is raised in the test.
            This is primarily for cocotb internal regression use for when a simulator error is expected.

            Users are encouraged to use the following idiom instead::

                @cocotb.test()
                async def my_test(dut):
                    try:
                        await thing_that_should_fail()
                    except ExceptionIExpect:
                        pass
                    else:
                        assert False, "Exception did not occur"

            .. versionchanged:: 1.3
                Specific exception types can be expected

            .. versionchanged:: 2.0
                Passing a :class:`bool` value was removed.
                Pass a specific :class:`Exception` or a tuple of Exceptions instead.

        skip:
            Don't execute this test as part of the regression. Test can still be run
            manually by setting :make:var:`COCOTB_TESTCASE`.

        stage:
            Order tests logically into stages, where multiple tests can share a stage.
            Defaults to 0.

        name:
            Override the default name of the test.
            The default test name is the :meth:`__qualname__` of the decorated test function.

            .. versionadded:: 2.0

    Returns:
        The test function to which the decorator is applied.

    .. note::

        To extend the test decorator, use the following template to create a new
        ``cocotb.test``\-like wrapper.

        .. code-block:: python

            import functools


            def test_extender(**decorator_kwargs):
                def decorator(obj):
                    @cocotb.test(**decorator_kwargs)
                    @functools.wraps(obj)
                    async def test(dut, **test_kwargs):
                        # your code here
                        ...

                    return obj

                return decorator

    .. versionchanged:: 2.0
        Support using decorator on test function without supplying parameters first.

        Assumes all default values for the test parameters.

        .. code-block:: python

            @cocotb.test
            async def test_thing(dut): ...


    .. versionchanged:: 2.0
        Decorated tests now return the decorated object.

    """
    if isinstance(obj, TestGenerator):
        return obj
    elif obj is not None:
        return TestGenerator(obj)

    def wrapper(obj: TestFuncType | TestGenerator) -> TestGenerator:
        if not isinstance(obj, TestGenerator):
            obj = TestGenerator(obj)
        if timeout_time is not None:
            obj.timeout = (timeout_time, timeout_unit)
        if expect_fail is not None:
            obj.expect_fail |= expect_fail
        if expect_error is not None:
            if isinstance(expect_error, type):
                obj.expect_error.add(expect_error)
            else:
                for exc in expect_error:
                    obj.expect_error.add(exc)
        if skip is not None:
            obj.skip |= skip
        if stage is not None:
            obj.stage = stage
        if name is not None:
            obj.name = name
        return obj

    return wrapper


def parametrize(
    *options_by_tuple: tuple[str, Sequence[object]]
    | tuple[Sequence[str], Sequence[Sequence[object]]],
    **options_by_name: Sequence[object],
) -> Callable[[TestFuncType | TestGenerator], TestGenerator]:
    """Decorator to generate parametrized tests from a single test function.

    Decorates a test function with named test parameters.
    The call to ``parametrize`` should include the name of each test parameter and the possible values each parameter can hold.
    This will generate a test for each of the Cartesian products of the parameters and their values.

    .. code-block:: python

        @cocotb.test(
            skip=False,
        )
        @cocotb.parametrize(
            arg1=[0, 1],
            arg2=["a", "b"],
        )
        async def my_test(arg1: int, arg2: str) -> None: ...

    The above is equivalent to the following.

    .. code-block:: python

        @cocotb.test(skip=False)
        async def my_test_0_a() -> None:
            arg1, arg2 = 0, "a"
            ...


        @cocotb.test(skip=False)
        async def my_test_0_b() -> None:
            arg1, arg2 = 0, "b"
            ...


        @cocotb.test(skip=False)
        async def my_test_1_a() -> None:
            arg1, arg2 = 1, "a"
            ...


        @cocotb.test(skip=False)
        async def my_test_1_b() -> None:
            arg1, arg2 = 1, "b"
            ...

    Options can also be specified in much the same way that :meth:`TestFactory.add_option <cocotb.regression.TestFactory.add_option>` can,
    either by supplying tuples of the parameter name to values,
    or a sequence of variable names and a sequence of values.

    .. code-block:: python

        @cocotb.parametrize(
            ("arg1", [0, 1]),
            (("arg2", "arg3"), [(1, 2), (3, 4)]),
        )
        async def my_test_2(arg1: int, arg2: int, arg3: int) -> None: ...

    Args:
        options_by_tuple:
            Tuple of parameter name to sequence of values for that parameter,
            or tuple of sequence of parameter names to sequence of sequences of values for that pack of parameters.

        options_by_name:
            Mapping of parameter name to sequence of values for that parameter.

    .. versionadded:: 2.0
    """

    # check good inputs
    for i, option_by_tuple in enumerate(options_by_tuple):
        if len(option_by_tuple) != 2:
            raise ValueError(
                f"Invalid option tuple {i}, expected exactly two fields `(name, values)`"
            )
        name, values = option_by_tuple
        if not isinstance(name, str):
            for n in name:
                if not n.isidentifier():
                    raise ValueError("Option names must be valid Python identifiers")
            values = cast("Sequence[Sequence[object]]", values)
            for value in values:
                if len(name) != len(value):
                    raise ValueError(
                        f"Invalid option tuple {i}, mismatching number of parameters ({name}) and values ({value})"
                    )
        elif not name.isidentifier():
            raise ValueError("Option names must be valid Python identifiers")

    def wrapper(f: TestFuncType | TestGenerator) -> TestGenerator:
        if not isinstance(f, TestGenerator):
            f = TestGenerator(f)
        # Ensure we prepend so that arguments lexically farther down in the "stack"
        # appear in the test name lexically after (more right).
        # Decorators are evaluated in reverse-lexical order.
        f.options = [*options_by_tuple, *options_by_name.items(), *f.options]
        return f

    return wrapper


def skipif(
    condition: bool, *, reason: str | None = None
) -> Callable[[TestFuncType | TestGenerator], TestGenerator]:
    """Marks a test as skipped if the condition is ``True``.

    This acts as an alternative to the ``skip`` option to :dec:`cocotb.test`.

    .. code-block:: python

        @cocotb.skipif(
            cocotb.top.USE_MY_FEATURE.value != 1,
            reason="The design doesn't support my feature.",
        )
        @cocotb.test
        async def test_my_feature(dut) -> None: ...

    Args:
        condition: The condition as to whether the test should be skipped. Defaults to ``True``.
        reason: A string giving the reason as to why this test was skipped.

            This argument is purely for documentation purposes.

    Returns:
        A decorator function to mark the test.
    """

    def decorator(obj: TestFuncType | TestGenerator) -> TestGenerator:
        if not isinstance(obj, TestGenerator):
            obj = TestGenerator(obj)
        obj.skip |= condition
        return obj

    return decorator
