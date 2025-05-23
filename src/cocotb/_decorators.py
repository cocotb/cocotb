# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import functools
import sys
from enum import Enum
from itertools import product
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from cocotb._test import Test
from cocotb._typing import TimeUnit

F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, None]])


class _Parameterized(Generic[F]):
    def __init__(
        self,
        test_function: F,
        options: List[
            Union[
                Tuple[str, Sequence[Any]], Tuple[Sequence[str], Sequence[Sequence[Any]]]
            ]
        ],
    ) -> None:
        self.test_function = test_function
        self.options = options
        # we are assuming the input checking is done in parametrize()

        self._option_reprs: Dict[str, List[str]] = {}

        for name, values in options:
            if isinstance(name, str):
                self._option_reprs[name] = _reprs(values)
            else:
                # transform to Dict[name, values]
                transformed: Dict[str, List[Optional[str]]] = {}
                for nam_idx, nam in enumerate(name):
                    transformed[nam] = []
                    for value_array in cast(Sequence[Sequence[Any]], values):
                        value = value_array[nam_idx]
                        transformed[nam].append(value)
                for n, vs in transformed.items():
                    self._option_reprs[n] = _reprs(vs)

    def generate_tests(
        self,
        *,
        name: Optional[str] = None,
        timeout_time: Optional[float] = None,
        timeout_unit: TimeUnit = "step",
        expect_fail: bool = False,
        expect_error: Union[Type[BaseException], Tuple[Type[BaseException], ...]] = (),
        skip: bool = False,
        stage: int = 0,
    ) -> Iterable[Test]:
        test_func_name = self.test_function.__qualname__ if name is None else name

        # this value is a list of ranges of the same length as each set of values in self.options for passing to itertools.product
        option_indexes = [range(len(option[1])) for option in self.options]

        # go through the cartesian product of all values of all options
        for selected_options in product(*option_indexes):
            test_kwargs: Dict[str, Sequence[Any]] = {}
            test_name_pieces: List[str] = [test_func_name]
            for option_idx, select_idx in enumerate(selected_options):
                option_name, option_values = self.options[option_idx]
                selected_value = option_values[select_idx]

                if isinstance(option_name, str):
                    # single params per option
                    selected_value = cast(Sequence[Any], selected_value)
                    test_kwargs[option_name] = selected_value
                    test_name_pieces.append(
                        f"/{option_name}={self._option_reprs[option_name][select_idx]}"
                    )
                else:
                    # multiple params per option
                    selected_value = cast(Sequence[Any], selected_value)
                    for n, v in zip(option_name, selected_value):
                        test_kwargs[n] = v
                        test_name_pieces.append(
                            f"/{n}={self._option_reprs[n][select_idx]}"
                        )

            parametrized_test_name = "".join(test_name_pieces)

            # create wrapper function to bind kwargs
            @functools.wraps(self.test_function)
            async def _my_test(
                dut: object, kwargs: Dict[str, Any] = test_kwargs
            ) -> None:
                await self.test_function(dut, **kwargs)

            yield Test(
                func=_my_test,
                name=parametrized_test_name,
                timeout_time=timeout_time,
                timeout_unit=timeout_unit,
                expect_fail=expect_fail,
                expect_error=expect_error,
                skip=skip,
                stage=stage,
            )


def _reprs(values: Sequence[Any]) -> List[str]:
    result: List[str] = []
    for value in values:
        value_repr = _repr(value)
        if value_repr is None:
            # non-representable value in option, so default to index strings and give up
            return [str(i) for i in range(len(values))]
        else:
            result.append(value_repr)
    return result


def _repr(v: Any) -> Optional[str]:
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
def test(_func: Union[F, _Parameterized[F]]) -> F: ...


@overload
def test(
    *,
    timeout_time: Optional[float] = None,
    timeout_unit: TimeUnit = "step",
    expect_fail: bool = False,
    expect_error: Union[Type[BaseException], Tuple[Type[BaseException], ...]] = (),
    skip: bool = False,
    stage: int = 0,
    name: Optional[str] = None,
) -> Callable[[Union[F, _Parameterized[F]]], F]: ...


def test(
    _func: Optional[Union[F, _Parameterized[F]]] = None,
    *,
    timeout_time: Optional[float] = None,
    timeout_unit: TimeUnit = "step",
    expect_fail: bool = False,
    expect_error: Union[Type[BaseException], Tuple[Type[BaseException], ...]] = (),
    skip: bool = False,
    stage: int = 0,
    name: Optional[str] = None,
) -> Union[F, Callable[[Union[F, _Parameterized[F]]], F]]:
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
                        pass  # your code here

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

    def _add_tests(module_name: str, *tests: Test) -> None:
        mod = sys.modules[module_name]
        if not hasattr(mod, "__cocotb_tests__"):
            setattr(mod, "__cocotb_tests__", [])
        cast(List[Test], mod.__cocotb_tests__).extend(tests)

    if _func is not None:
        if isinstance(_func, _Parameterized):
            test_func = _func.test_function
            _add_tests(test_func.__module__, *_func.generate_tests())
            return test_func
        else:
            _add_tests(_func.__module__, Test(func=_func))
            return _func

    def wrapper(f: Union[F, _Parameterized[F]]) -> F:
        if isinstance(f, _Parameterized):
            test_func = f.test_function
            _add_tests(
                test_func.__module__,
                *f.generate_tests(
                    name=name,
                    timeout_time=timeout_time,
                    timeout_unit=timeout_unit,
                    expect_fail=expect_fail,
                    expect_error=expect_error,
                    skip=skip,
                    stage=stage,
                ),
            )
            return test_func
        else:
            _add_tests(
                f.__module__,
                Test(
                    func=f,
                    name=name,
                    timeout_time=timeout_time,
                    timeout_unit=timeout_unit,
                    expect_fail=expect_fail,
                    expect_error=expect_error,
                    skip=skip,
                    stage=stage,
                ),
            )
            return f

    return wrapper


def parametrize(
    *options_by_tuple: Union[
        Tuple[str, Sequence[Any]], Tuple[Sequence[str], Sequence[Sequence[Any]]]
    ],
    **options_by_name: Sequence[Any],
) -> Callable[[F], _Parameterized[F]]:
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
            (("arg2", "arg3"), [(1, 2), (3, 4)])
        )

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
            values = cast(Sequence[Sequence[Any]], values)
            for value in values:
                if len(name) != len(value):
                    raise ValueError(
                        f"Invalid option tuple {i}, mismatching number of parameters ({name}) and values ({value})"
                    )
        elif not name.isidentifier():
            raise ValueError("Option names must be valid Python identifiers")

    options = [*options_by_tuple, *options_by_name.items()]

    def wrapper(f: F) -> _Parameterized[F]:
        return _Parameterized(f, options)

    return wrapper
