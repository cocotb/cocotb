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

import sys
import functools
import inspect
import os
import warnings
import collections.abc

import cocotb
from cocotb.log import SimLog
from cocotb.result import ReturnValue
from cocotb.utils import lazy_property, remove_traceback_frames, extract_coro_stack
from cocotb import outcomes

# Sadly the Python standard logging module is very slow so it's better not to
# make any calls by testing a boolean flag first
if "COCOTB_SCHEDULER_DEBUG" in os.environ:
    _debug = True
else:
    _debug = False


def public(f):
    """Use a decorator to avoid retyping function/class names.

    * Based on an idea by Duncan Booth:
    http://groups.google.com/group/comp.lang.python/msg/11cbb03e09611b8a
    * Improved via a suggestion by Dave Angel:
    http://groups.google.com/group/comp.lang.python/msg/3d400fb22d8a42e1
    """
    all = sys.modules[f.__module__].__dict__.setdefault('__all__', [])
    if f.__name__ not in all:  # Prevent duplicates if run from an IDE.
        all.append(f.__name__)
    return f


public(public)  # Emulate decorating ourself


@public
class CoroutineComplete(Exception):
    """To ensure that a coroutine has completed before we fire any triggers
    that are blocked waiting for the coroutine to end, we create a sub-class
    exception that the scheduler catches and the callbacks are attached
    here.
    """

    def __init__(self, text=""):
        Exception.__init__(self, text)


class RunningTask:
    """Per instance wrapper around a running generator.

    Provides the following:

        task.join() creates a Trigger that will fire when this coroutine
        completes.

        task.kill() will destroy a coroutine instance (and cause any Join
        triggers to fire.
    """

    _name: str = "Task"  # class name of schedulable task
    _id_count = 0  # used by the scheduler for debug

    def __init__(self, inst):

        if isinstance(inst, collections.abc.Coroutine):
            self._natively_awaitable = True
        elif inspect.isgenerator(inst):
            self._natively_awaitable = False
        elif inspect.iscoroutinefunction(inst):
            raise TypeError(
                "Coroutine function {} should be called prior to being "
                "scheduled."
                .format(inst))
        elif inspect.isasyncgen(inst):
            raise TypeError(
                "{} is an async generator, not a coroutine. "
                "You likely used the yield keyword instead of await.".format(
                    inst.__qualname__))
        else:
            raise TypeError(
                "%s isn't a valid coroutine! Did you forget to use the yield keyword?" % inst)
        self._coro = inst
        self._started = False
        self._callbacks = []
        self._outcome = None
        self._trigger = None

        self._task_id = self._id_count
        RunningTask._id_count += 1
        self.__name__ = f"{type(self)._name} {self._task_id}"
        self.__qualname__ = self.__name__

    @lazy_property
    def log(self):
        # Creating a logger is expensive, only do it if we actually plan to
        # log anything
        return SimLog("cocotb.coroutine.%s" % self.__qualname__, id(self))

    @property
    def retval(self):
        if self._outcome is None:
            raise RuntimeError("coroutine is not complete")
        return self._outcome.get()

    @property
    def _finished(self):
        return self._outcome is not None

    def __iter__(self):
        return self

    def __str__(self):
        return f"<{self.__name__}>"

    def _get_coro_stack(self):
        """Get the coroutine callstack of this Task."""
        coro_stack = extract_coro_stack(self._coro)

        # Remove Trigger.__await__() from the stack, as it's not really useful
        if self._natively_awaitable and len(coro_stack):
            if coro_stack[-1].name == '__await__':
                coro_stack.pop()

        return coro_stack

    def __repr__(self):
        coro_stack = self._get_coro_stack()

        if cocotb.scheduler._current_task is self:
            fmt = "<{name} running coro={coro}()>"
        elif self._finished:
            fmt = "<{name} finished coro={coro}() outcome={outcome}>"
        elif self._trigger is not None:
            fmt = "<{name} pending coro={coro}() trigger={trigger}>"
        elif not self._started:
            fmt = "<{name} created coro={coro}()>"
        else:
            fmt = "<{name} adding coro={coro}()>"

        try:
            coro_name = coro_stack[-1].name
        # coro_stack may be empty if:
        # - exhausted generator
        # - finished coroutine
        except IndexError:
            coro_name = self._coro.__name__

        repr_string = fmt.format(
            name=self.__name__,
            coro=coro_name,
            trigger=self._trigger,
            outcome=self._outcome
        )
        return repr_string

    def _advance(self, outcome):
        """Advance to the next yield in this coroutine.

        Args:
            outcome: The :any:`outcomes.Outcome` object to resume with.

        Returns:
            The object yielded from the coroutine

        Raises:
            CoroutineComplete: If the coroutine returns or throws an error, self._outcome is set, and
           :exc:`CoroutineComplete` is thrown.
        """
        try:
            self._started = True
            return outcome.send(self._coro)
        except ReturnValue as e:
            self._outcome = outcomes.Value(e.retval)
            raise CoroutineComplete()
        except StopIteration as e:
            self._outcome = outcomes.Value(e.value)
            raise CoroutineComplete()
        except BaseException as e:
            self._outcome = outcomes.Error(remove_traceback_frames(e, ['_advance', 'send']))
            raise CoroutineComplete()

    def send(self, value):
        return self._coro.send(value)

    def throw(self, exc):
        return self._coro.throw(exc)

    def close(self):
        return self._coro.close()

    def kill(self):
        """Kill a coroutine."""
        if self._outcome is not None:
            # already finished, nothing to kill
            return

        if _debug:
            self.log.debug("kill() called on coroutine")
        # todo: probably better to throw an exception for anyone waiting on the coroutine
        self._outcome = outcomes.Value(None)
        cocotb.scheduler._unschedule(self)

    def join(self):
        """Return a trigger that will fire when the wrapped coroutine exits."""
        return cocotb.triggers.Join(self)

    def has_started(self):
        return self._started

    def __bool__(self):
        """Provide boolean testing
            if the coroutine has finished return false
            otherwise return true"""
        return not self._finished

    def __await__(self):
        # It's tempting to use `return (yield from self._coro)` here,
        # which bypasses the scheduler. Unfortunately, this means that
        # we can't keep track of the result or state of the coroutine,
        # things which we expose in our public API. If you want the
        # efficiency of bypassing the scheduler, remove the `@coroutine`
        # decorator from your `async` functions.

        # Hand the coroutine back to the scheduler trampoline.
        return (yield self)


class RunningCoroutine(RunningTask):
    """
    The result of calling a :any:`cocotb.coroutine` decorated coroutine.

    All this class does is provide some extra attributes.
    """

    def __init__(self, inst, parent):
        RunningTask.__init__(self, inst)
        self._parent = parent
        self.__doc__ = parent._func.__doc__
        self.module = parent._func.__module__
        self.funcname = parent._func.__name__


class RunningTest(RunningCoroutine):
    """
    The result of calling a :class:`cocotb.test` decorated object.

    All this class does is change ``__name__`` to show "Test" instead of "Task".
    """

    _name: str = "Test"


class coroutine:
    """Decorator class that allows us to provide common coroutine mechanisms:

    ``log`` methods will log to ``cocotb.coroutine.name``.

    :meth:`~cocotb.decorators.RunningTask.join` method returns an event which will fire when the coroutine exits.

    Used as ``@cocotb.coroutine``.
    """

    def __init__(self, func):
        self._func = func
        functools.update_wrapper(self, func)

    @lazy_property
    def log(self):
        return SimLog("cocotb.coroutine.%s" % self._func.__qualname__, id(self))

    def __call__(self, *args, **kwargs):
        return RunningCoroutine(self._func(*args, **kwargs), self)

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
        return SimLog("cocotb.function.%s" % self._coro.__qualname__, id(self))

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
        self._log = SimLog("cocotb.external.%s" % self._func.__qualname__, id(self))

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
                Using None as the the *timeout_unit* argument is deprecated, use ``'step'`` instead.

        expect_fail (bool, optional):
            Don't mark the result as a failure if the test fails.

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

        stage (int, optional)
            Order tests logically into stages, where multiple tests can share a stage.
    """

    _id_count = 0  # used by the RegressionManager to sort tests in definition order

    def __init__(self, f, timeout_time=None, timeout_unit="step",
                 expect_fail=False, expect_error=(),
                 skip=False, stage=None):

        if timeout_unit is None:
            warnings.warn(
                'Using timeout_unit=None is deprecated, use timeout_unit="step" instead.',
                DeprecationWarning, stacklevel=2)
            timeout_unit="step"  # don't propagate deprecated value
        self._id = self._id_count
        type(self)._id_count += 1

        if timeout_time is not None:
            co = coroutine(f)

            @functools.wraps(f)
            async def f(*args, **kwargs):
                running_co = co(*args, **kwargs)

                try:
                    res = await cocotb.triggers.with_timeout(running_co, self.timeout_time, self.timeout_unit)
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
                DeprecationWarning, stacklevel=2)
        if expect_error is True:
            expect_error = (Exception,)
        elif expect_error is False:
            expect_error = ()
        self.expect_error = expect_error
        self.skip = skip
        self.stage = stage
        self.im_test = True    # For auto-regressions
        self.name = self._func.__name__

    def __call__(self, *args, **kwargs):
        inst = self._func(*args, **kwargs)
        coro = RunningTest(inst, self)
        return coro
