# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd,
#       SolarFlare Communications Inc nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

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

import cocotb
from cocotb.regression import Test

Result = TypeVar("Result")


def function(func: Callable[..., Coroutine[Any, Any, Result]]) -> Callable[..., Result]:
    """Decorator that turns a :term:`coroutine function` into a blocking function.

    This allows an :keyword:`async` function that yields to the simulator and consumes simulation time
    to be called by a thread started with :class:`cocotb.external`.
    When the returned blocking function is called, a new :class:`~cocotb.task.Task` is constructed
    from the :keyword:`async` function, passing through any arguments provided by the caller,
    and scheduled on the main thread.
    The external caller thread will block until the task finishes,
    and the result will be returned to the caller of the blocking function.

    Args:
        func: The :term:`coroutine function` to wrap/convert.

    Returns:
        The function to be called.

    Raises:
        RuntimeError: If the blocking function that is returned is subsequently called from a thread that was not started with :class:`cocotb.external`.

    .. versionchanged:: 2.0
        No longer implemented as a unique type.
        The ``log`` attribute is no longer available.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return cocotb._scheduler._queue_function(func(*args, **kwargs))

    return wrapper


def external(func: Callable[..., Result]) -> Callable[..., Coroutine[Any, Any, Result]]:
    """Decorator that turns a blocking function into a :term:`coroutine function`.

    When the returned :keyword:`async` function is called, it creates a coroutine object
    that can be directly :keyword:`await`\ ed or constructed into a :class:`~cocotb.task.Task`.
    The coroutine will suspend the awaiting task until the wrapped function completes in its thread,
    and the result of the function will be returned from the coroutine.
    Currently, this creates a new execution thread for each function that is called.

    Args:
        func: The function to run externally.

    Returns:
        The :term:`coroutine function`.

    .. versionchanged:: 2.0
        No longer implemented as a unique type.
        The ``log`` attribute is no longer available.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return cocotb._scheduler._run_in_executor(func, *args, **kwargs)

    return wrapper


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
        # we are assuming the input checking is done in parameterize()

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
        timeout_unit: str = "step",
        expect_fail: bool = False,
        expect_error: Union[Type[Exception], Sequence[Type[Exception]]] = (),
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

            parameterized_test_name = "".join(test_name_pieces)

            # create wrapper function to bind kwargs
            @functools.wraps(self.test_function)
            async def _my_test(dut, kwargs: Dict[str, Any] = test_kwargs) -> None:
                await self.test_function(dut, **kwargs)

            yield Test(
                func=_my_test,
                name=parameterized_test_name,
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
    if isinstance(v, str):
        if len(v) <= 10 and v.isidentifier():
            return v
        else:
            return None
    elif isinstance(v, (int, float, bool, type(None))):
        return repr(v)
    elif isinstance(v, Enum):
        return v.name
    elif isinstance(v, type):
        return v.__qualname__
    elif callable(v) and hasattr(v, "__qualname__"):
        return v.__qualname__
    else:
        return None


@overload
def test(_func: Union[F, _Parameterized[F]]) -> F: ...


@overload
def test(
    *,
    timeout_time: Optional[float] = None,
    timeout_unit: str = "step",
    expect_fail: bool = False,
    expect_error: Union[Type[Exception], Sequence[Type[Exception]]] = (),
    skip: bool = False,
    stage: int = 0,
    name: Optional[str] = None,
) -> Callable[[Union[F, _Parameterized[F]]], F]: ...


def test(
    _func: Optional[Union[F, _Parameterized[F]]] = None,
    *,
    timeout_time: Optional[float] = None,
    timeout_unit: str = "step",
    expect_fail: bool = False,
    expect_error: Union[Type[Exception], Sequence[Type[Exception]]] = (),
    skip: bool = False,
    stage: int = 0,
    name: Optional[str] = None,
) -> Callable[[Union[F, _Parameterized[F]]], F]:
    """
    Decorator to register a Callable which returns a Coroutine as a test.

    The test decorator provides a test timeout, and allows us to mark tests as skipped or expecting errors or failures.
    Tests are evaluated in the order they are defined in a test module.

    Usage:
        .. code-block:: python3

            @cocotb.test(timeout_time=10, timeout_unit="ms")
            async def test_thing(dut): ...

    .. versionchanged:: 2.0
        Support using decorator on test function without supplying parameters first.

        Assumes all default values for the test parameters.

        .. code-block:: python3

            @cocotb.test
            async def test_thing(dut): ...

    .. versionchanged:: 2.0
        Decorated tests now return the decorated object.

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
            If ``True`` and the test fails a functional check via an ``assert`` statement, :class:`pytest.raises`,
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
            manually by setting :make:var:`TESTCASE`.

        stage:
            Order tests logically into stages, where multiple tests can share a stage.
            Defaults to 0.

        name:
            Override the default name of the test.
            The default test name is the :any:`__qualname__` of the decorated test function.

            .. versionadded:: 2.0

    Returns:
        The test function to which the decorator is applied.
    """

    def _add_tests(module_name: str, *tests: Test) -> None:
        mod = sys.modules[module_name]
        if not hasattr(mod, "__cocotb_tests__"):
            mod.__cocotb_tests__ = []
        mod.__cocotb_tests__.extend(tests)

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


def parameterize(
    *options_by_tuple: Union[
        Tuple[str, Sequence[Any]], Tuple[Sequence[str], Sequence[Sequence[Any]]]
    ],
    **options_by_name: Sequence[Any],
) -> Callable[[F], _Parameterized[F]]:
    """Decorator to generate parameterized tests from a single test function.

    Decorates a test function with named test parameters.
    The call to ``parameterize`` should include the name of each test parameter and the possible values each parameter can hold.
    This will generate a test for each of the Cartesian products of the parameters and their values.

    .. code-block:: python3

        @cocotb.test(
            skip=False,
        )
        @cocotb.parameterize(
            arg1=[0, 1],
            arg2=["a", "b"],
        )
        async def my_test(arg1: int, arg2: str) -> None: ...

    The above is equivalent to the following.

    .. code-block:: python3

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

    .. code-block:: python3

        @cocotb.parameterize(
            ("arg1", [0, 1]),
            (("arg2", arg3"), [(1, 2), (3, 4)])
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
