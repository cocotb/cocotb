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
import typing
import warnings

import cocotb
import cocotb.triggers
from cocotb.log import SimLog
from cocotb.task import Task as _Task  # noqa: F401
from cocotb.task import _RunningCoroutine, _RunningTest
from cocotb.utils import lazy_property


def public(f):
    """Use a decorator to avoid retyping function/class names.

    * Based on an idea by Duncan Booth:
    http://groups.google.com/group/comp.lang.python/msg/11cbb03e09611b8a
    * Improved via a suggestion by Dave Angel:
    http://groups.google.com/group/comp.lang.python/msg/3d400fb22d8a42e1
    """
    all = sys.modules[f.__module__].__dict__.setdefault("__all__", [])
    if f.__name__ not in all:  # Prevent duplicates if run from an IDE.
        all.append(f.__name__)
    return f


public(public)  # Emulate decorating ourself


class coroutine:
    """Decorator class that allows us to provide common coroutine mechanisms:

    ``log`` methods will log to ``cocotb.coroutine.name``.

    :meth:`~cocotb.task.Task.join` method returns an event which will fire when the coroutine exits.

    Used as ``@cocotb.coroutine``.
    """

    def __init__(self, func):
        self._func = func
        functools.update_wrapper(self, func)

    @lazy_property
    def log(self):
        return SimLog(f"cocotb.coroutine.{self._func.__qualname__}.{id(self)}")

    def __call__(self, *args, **kwargs):
        return _RunningCoroutine(self._func(*args, **kwargs), self)

    def __get__(self, obj, owner=None):
        """Permit the decorator to be used on class methods
        and standalone functions"""
        return type(self)(self._func.__get__(obj, owner))

    def __iter__(self):
        return self

    def __str__(self):
        return str(self._func.__qualname__)


@public
class function:
    """Decorator class that allows a function to block.

    This allows a coroutine that consumes simulation time
    to be called by a thread started with :class:`cocotb.external`;
    in other words, to internally block while externally
    appear to yield.
    """

    def __init__(self, func):
        self._coro = cocotb.coroutine(func)

    @lazy_property
    def log(self):
        return SimLog(f"cocotb.function.{self._coro.__qualname__}.{id(self)}")

    def __call__(self, *args, **kwargs):
        return cocotb.scheduler._queue_function(self._coro(*args, **kwargs))

    def __get__(self, obj, owner=None):
        """Permit the decorator to be used on class methods
        and standalone functions"""
        return type(self)(self._coro._func.__get__(obj, owner))


@public
class external:
    """Decorator to apply to an external function to enable calling from cocotb.

    This turns a normal function that isn't a coroutine into a blocking coroutine.
    Currently, this creates a new execution thread for each function that is
    called.
    Scope for this to be streamlined to a queue in future.
    """

    def __init__(self, func):
        self._func = func
        self._log = SimLog(f"cocotb.external.{self._func.__qualname__}.{id(self)}")

    def __call__(self, *args, **kwargs):
        return cocotb.scheduler._run_in_executor(self._func, *args, **kwargs)

    def __get__(self, obj, owner=None):
        """Permit the decorator to be used on class methods
        and standalone functions"""
        return type(self)(self._func.__get__(obj, owner))


class _decorator_helper(type):
    """
    Metaclass that allows a type to be constructed using decorator syntax,
    passing the decorated function as the first argument.

    So:

        @MyClass(construction, args='go here')
        def this_is_passed_as_f(...):
            pass

    ends up calling

        MyClass.__init__(this_is_passed_as_f, construction, args='go here')
    """

    def __call__(cls, *args, **kwargs):
        def decorator(f):
            # fall back to the normal way of constructing an object, now that
            # we have all the arguments
            return type.__call__(cls, f, *args, **kwargs)

        return decorator


@public
class test(coroutine, metaclass=_decorator_helper):
    """
    Decorator to mark a Callable which returns a Coroutine as a test.

    The test decorator provides a test timeout, and allows us to mark tests as skipped
    or expecting errors or failures.
    Tests are evaluated in the order they are defined in a test module.

    Used as ``@cocotb.test(...)``.

    Args:
        timeout_time (numbers.Real or decimal.Decimal, optional):
            Simulation time duration before timeout occurs.

            .. versionadded:: 1.3

            .. note::
                Test timeout is intended for protection against deadlock.
                Users should use :class:`~cocotb.triggers.with_timeout` if they require a
                more general-purpose timeout mechanism.

        timeout_unit (str, optional):
            Units of timeout_time, accepts any units that :class:`~cocotb.triggers.Timer` does.

            .. versionadded:: 1.3

            .. deprecated:: 1.5
                Using ``None`` as the *timeout_unit* argument is deprecated, use ``'step'`` instead.

        expect_fail (bool, optional):
            If ``True`` and the test fails a functional check via an ``assert`` statement, :class:`pytest.raises`,
            :class:`pytest.warns`, or :class:`pytest.deprecated_call` the test is considered to have passed.
            If ``True`` and the test passes successfully, the test is considered to have failed.

        expect_error (exception type or tuple of exception types, optional):
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

            .. deprecated:: 1.5
                Passing a :class:`bool` value is now deprecated.
                Pass a specific :class:`Exception` or a tuple of Exceptions instead.

        skip (bool, optional):
            Don't execute this test as part of the regression. Test can still be run
            manually by setting :make:var:`TESTCASE`.

        stage (int)
            Order tests logically into stages, where multiple tests can share a stage.
            Defaults to 0.
    """

    _id_count = 0  # used by the RegressionManager to sort tests in definition order

    def __init__(
        self,
        f,
        timeout_time=None,
        timeout_unit="step",
        expect_fail=False,
        expect_error=(),
        skip=False,
        stage=0,
    ):

        if timeout_unit is None:
            warnings.warn(
                'Using timeout_unit=None is deprecated, use timeout_unit="step" instead.',
                DeprecationWarning,
                stacklevel=2,
            )
            timeout_unit = "step"  # don't propagate deprecated value
        self._id = self._id_count
        type(self)._id_count += 1

        if timeout_time is not None:
            co = coroutine(f)

            @functools.wraps(f)
            async def f(*args, **kwargs):
                running_co = co(*args, **kwargs)

                try:
                    res = await cocotb.triggers.with_timeout(
                        running_co, self.timeout_time, self.timeout_unit
                    )
                except cocotb.result.SimTimeoutError:
                    running_co.kill()
                    raise
                else:
                    return res

        super().__init__(f)

        self.timeout_time = timeout_time
        self.timeout_unit = timeout_unit
        self.expect_fail = expect_fail
        if isinstance(expect_error, bool):
            warnings.warn(
                "Passing bool values to `except_error` option of `cocotb.test` is deprecated. "
                "Pass a specific Exception type instead",
                DeprecationWarning,
                stacklevel=2,
            )
        if expect_error is True:
            expect_error = (BaseException,)
        elif expect_error is False:
            expect_error = ()
        self.expect_error = expect_error
        self.skip = skip
        self.stage = stage
        self.im_test = True  # For auto-regressions
        self.name = self._func.__name__

    def __call__(self, *args, **kwargs):
        inst = self._func(*args, **kwargs)
        coro = _RunningTest(inst, self)
        return coro


if sys.version_info < (3, 7):
    Task = _Task
    RunningTask = _Task
    RunningCoroutine = _RunningCoroutine
    RunningTest = _RunningTest
else:

    def __getattr__(attr: str) -> typing.Any:
        if attr in ("Task", "RunningTask"):
            warnings.warn(
                f"The class {attr} has been renamed to cocotb.task.Task.",
                DeprecationWarning,
                stacklevel=2,
            )
            attr = "_Task"
        elif attr in ("RunningCoroutine", "RunningTest"):
            warnings.warn(
                f"The class {attr} is now private. Update all uses to the parent class cocotb.task.Task.",
                DeprecationWarning,
                stacklevel=2,
            )
            attr = f"_{attr}"
        try:
            return globals()[attr]
        except KeyError:
            raise AttributeError(
                f"module {__name__!r} has no attribute {attr!r}"
            ) from None
