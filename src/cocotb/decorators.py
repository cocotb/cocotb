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
from typing import (
    Any,
    Callable,
    Coroutine,
    List,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    overload,
)

import cocotb
from cocotb.regression import TestFactory

Result = TypeVar("Result")


def function(func: Callable[..., Coroutine[Any, Any, Result]]) -> Callable[..., Result]:
    """Decorator that turns a :term:`coroutine function` into a blocking function.

    This allows a coroutine that consumes simulation time
    to be called by a thread started with :class:`cocotb.external`;
    in other words, to internally block while externally
    appear to yield.

    .. versionchanged:: 2.0
        No longer implemented as a unique type.
        The ``log`` attribute is no longer available.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return cocotb.scheduler._queue_function(func(*args, **kwargs))

    return wrapper


def external(func: Callable[..., Result]) -> Callable[..., Coroutine[Any, Any, Result]]:
    """Decorator that turns a blocking function into a :term:`coroutine function`.

    This turns a normal function that isn't a coroutine into a blocking coroutine.
    Currently, this creates a new execution thread for each function that is
    called.

    .. versionchanged:: 2.0
        No longer implemented as a unique type.
        The ``log`` attribute is no longer available.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return cocotb.scheduler._run_in_executor(func, *args, **kwargs)

    return wrapper


F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, None]])


@overload
def test(_func: Union[F, TestFactory[F]]) -> F:
    ...


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
) -> Callable[[Union[F, TestFactory[F]]], F]:
    ...


def test(
    _func: Optional[Union[F, TestFactory[F]]] = None,
    *,
    timeout_time: Optional[float] = None,
    timeout_unit: str = "step",
    expect_fail: bool = False,
    expect_error: Union[Type[Exception], Sequence[Type[Exception]]] = (),
    skip: bool = False,
    stage: int = 0,
    name: Optional[str] = None,
) -> Callable[[Union[F, TestFactory[F]]], F]:
    """
    Decorator to register a Callable which returns a Coroutine as a test.

    The test decorator provides a test timeout, and allows us to mark tests as skipped or expecting errors or failures.
    Tests are evaluated in the order they are defined in a test module.

    Usage:
        .. code-block:: python3

            @cocotb.test(timeout_time=10, timeout_unit="ms")
            async def test_thing(dut):
                ...

    .. versionchanged:: 2.0
        Support using decorator on test function without supplying parameters first.

        Assumes all default values for the test parameters.

        .. code-block:: python3

            @cocotb.test
            async def test_thing(dut):
                ...

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

    if _func is not None:
        if isinstance(_func, TestFactory):
            if cocotb.regression_manager is not None:
                _func.generate_tests()
            return _func.test_function
        else:
            if cocotb.regression_manager is not None:
                cocotb.regression_manager.register_test(func=_func)
            return _func

    def wrapper(f: Union[F, TestFactory[F]]) -> F:
        if isinstance(f, TestFactory):
            if cocotb.regression_manager is not None:
                f.generate_tests(
                    name=name,
                    timeout_time=timeout_time,
                    timeout_unit=timeout_unit,
                    expect_fail=expect_fail,
                    expect_error=expect_error,
                    skip=skip,
                    stage=stage,
                )
            return f.test_function

        else:
            if cocotb.regression_manager is not None:
                cocotb.regression_manager.register_test(
                    func=f,
                    name=name,
                    timeout_time=timeout_time,
                    timeout_unit=timeout_unit,
                    expect_fail=expect_fail,
                    expect_error=expect_error,
                    skip=skip,
                    stage=stage,
                )
            return f

    return wrapper


def parameterize(
    **kwargs: List[Any],
) -> Callable[[Callable[..., Coroutine[Any, Any, None]]], TestFactory]:
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
        async def my_test(arg1: int, arg2: str) -> None:
            ...

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

    Args:
        kwargs:
            Mapping of test function parameter names to the list of values each

    .. versionadded:: 2.0
    """

    for key, lis in kwargs.items():
        if not isinstance(lis, list):
            raise TypeError(
                f"All arguments to parameterize must be lists, got {key}={lis}({type(lis)})"
            )

    def wrapper(f):
        tf = TestFactory(f)
        for key, lis in kwargs.items():
            tf.add_option(key, lis)
        return tf

    return wrapper
