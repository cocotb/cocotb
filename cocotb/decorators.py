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

from __future__ import print_function
import sys
import time
import logging
import traceback
import pdb
import functools
import threading

from io import StringIO, BytesIO

import cocotb
from cocotb.log import SimLog
from cocotb.triggers import Join, PythonTrigger, Timer, Event, NullTrigger
from cocotb.result import (TestComplete, TestError, TestFailure, TestSuccess,
                           ReturnValue, raise_error, ExternalException)
from cocotb.utils import get_sim_time
from cocotb import outcomes


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
    that are blocked waiting for the coroutine to end, we create a subclass
    exception that the Scheduler catches and the callbacks are attached
    here.
    """
    def __init__(self, text=""):
        Exception.__init__(self, text)


class RunningCoroutine(object):
    """Per instance wrapper around an function to turn it into a coroutine.

    Provides the following:

        coro.join() creates a Trigger that will fire when this coroutine
        completes.

        coro.kill() will destroy a coroutine instance (and cause any Join
        triggers to fire.
    """
    def __init__(self, inst, parent):
        if hasattr(inst, "__name__"):
            self.__name__ = "%s" % inst.__name__
            self.log = SimLog("cocotb.coroutine.%s" % self.__name__, id(self))
        else:
            self.log = SimLog("cocotb.coroutine.fail")
        self._coro = inst
        self._started = False
        self._callbacks = []
        self._parent = parent
        self.__doc__ = parent._func.__doc__
        self.module = parent._func.__module__
        self.funcname = parent._func.__name__
        self._outcome = None

        if not hasattr(self._coro, "send"):
            self.log.error("%s isn't a valid coroutine! Did you use the yield "
                           "keyword?" % self.funcname)
            raise CoroutineComplete()

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
        return str(self.__name__)

    def _advance(self, outcome):
        """
        Advance to the next yield in this coroutine

        :param outcome: The `outcomes.Outcome` object to resume with.
        :returns: The object yielded from the coroutine

        If the coroutine returns or throws an error, self._outcome is set, and
        this throws `CoroutineComplete`.
        """
        try:
            self._started = True
            return outcome.send(self._coro)
        except ReturnValue as e:
            self._outcome = outcomes.Value(e.retval)
            raise CoroutineComplete()
        except StopIteration as e:
            retval = getattr(e, 'value', None)  # for python >=3.3
            self._outcome = outcomes.Value(retval)
            raise CoroutineComplete()
        except BaseException as e:
            self._outcome = outcomes.Error(e)
            raise CoroutineComplete()

    def send(self, value):
        return self._coro.send(value)

    def throw(self, exc):
        return self._coro.throw(exc)

    def close(self):
        return self._coro.close()

    def kill(self):
        """Kill a coroutine."""
        self.log.debug("kill() called on coroutine")
        # todo: probably better to throw an exception for anyone waiting on the coroutine
        self._outcome = outcomes.Value(None)
        cocotb.scheduler.unschedule(self)

    def join(self):
        """Return a trigger that will fire when the wrapped coroutine exits."""
        return Join(self)

    def has_started(self):
        return self._started

    def __nonzero__(self):
        """Provide boolean testing
            if the coroutine has finished return false
            otherwise return true"""
        return not self._finished

    __bool__ = __nonzero__

    def sort_name(self):
        if self.stage is None:
            return "%s.%s" % (self.module, self.funcname)
        else:
            return "%s.%d.%s" % (self.module, self.stage, self.funcname)

class RunningTest(RunningCoroutine):
    """Add some useful Test functionality to a RunningCoroutine."""

    class ErrorLogHandler(logging.Handler):
        def __init__(self, fn):
            self.fn = fn
            logging.Handler.__init__(self, level=logging.DEBUG)

        def handle(self, record):
            self.fn(self.format(record))

    def __init__(self, inst, parent):
        self.error_messages = []
        RunningCoroutine.__init__(self, inst, parent)
        self.started = False
        self.start_time = 0
        self.start_sim_time = 0
        self.expect_fail = parent.expect_fail
        self.expect_error = parent.expect_error
        self.skip = parent.skip
        self.stage = parent.stage

        self.handler = RunningTest.ErrorLogHandler(self._handle_error_message)
        cocotb.log.addHandler(self.handler)

    def _advance(self, outcome):
        if not self.started:
            self.error_messages = []
            self.log.info("Starting test: \"%s\"\nDescription: %s" %
                          (self.funcname, self.__doc__))
            self.start_time = time.time()
            self.start_sim_time = get_sim_time('ns')
            self.started = True
        try:
            self.log.debug("Sending {}".format(outcome))
            return outcome.send(self._coro)
        except TestComplete as e:
            if isinstance(e, TestFailure):
                self.log.warning(str(e))
            else:
                self.log.info(str(e))

            buff = StringIO()
            for message in self.error_messages:
                print(message, file=buff)
            e.stderr.write(buff.getvalue())
            raise
        except StopIteration:
            raise TestSuccess()
        except Exception as e:
            raise raise_error(self, "Send raised exception:")

    def _handle_error_message(self, msg):
        self.error_messages.append(msg)


class coroutine(object):
    """Decorator class that allows us to provide common coroutine mechanisms:

    ``log`` methods will will log to ``cocotb.coroutines.name``.

    ``join()`` method returns an event which will fire when the coroutine exits.
    """

    def __init__(self, func):
        self._func = func
        self.log = SimLog("cocotb.function.%s" % self._func.__name__, id(self))
        self.__name__ = self._func.__name__
        functools.update_wrapper(self, func)

    def __call__(self, *args, **kwargs):
        try:
            return RunningCoroutine(self._func(*args, **kwargs), self)
        except Exception as e:
            traceback.print_exc()
            result = TestError(str(e))
            if sys.version_info[0] >= 3:
                buff = StringIO()
                traceback.print_exc(file=buff)
            else:
                buff_bytes = BytesIO()
                traceback.print_exc(file=buff_bytes)
                buff = StringIO(buff_bytes.getvalue().decode("UTF-8"))
            result.stderr.write(buff.getvalue())
            raise result

    def __get__(self, obj, type=None):
        """Permit the decorator to be used on class methods
            and standalone functions"""
        return self.__class__(self._func.__get__(obj, type))

    def __iter__(self):
        return self

    def __str__(self):
        return str(self._func.__name__)


@public
class function(object):
    """Decorator class that allows a function to block.

    This allows a function to internally block while
    externally appear to yield.
    """
    def __init__(self, func):
        self._func = func
        self.log = SimLog("cocotb.function.%s" % self._func.__name__, id(self))

    def __call__(self, *args, **kwargs):

        @coroutine
        def execute_function(self, event):
            coro = cocotb.coroutine(self._func)(*args, **kwargs)
            try:
                _outcome = outcomes.Value((yield coro))
            except BaseException as e:
                _outcome = outcomes.Error(e)
            event.outcome = _outcome
            event.set()

        self._event = threading.Event()
        self._event.result = None
        waiter = cocotb.scheduler.queue_function(execute_function(self, self._event))
        # This blocks the calling external thread until the coroutine finishes
        self._event.wait()
        waiter.thread_resume()
        return self._event.outcome.get()

    def __get__(self, obj, type=None):
        """Permit the decorator to be used on class methods
            and standalone functions"""
        return self.__class__(self._func.__get__(obj, type))

@public
class external(object):
    """Decorator to apply to an external function to enable calling from cocotb.
    This currently creates a new execution context for each function that is
    called. Scope for this to be streamlined to a queue in future.
    """
    def __init__(self, func):
        self._func = func
        self._log = SimLog("cocotb.external.%s" % self._func.__name__, id(self))

    def __call__(self, *args, **kwargs):

        @coroutine
        def wrapper():
            ext = cocotb.scheduler.run_in_executor(self._func, *args, **kwargs)
            yield ext.event.wait()

            ret = ext.result  # raises if there was an exception
            raise ReturnValue(ret)

        return wrapper()

    def __get__(self, obj, type=None):
        """Permit the decorator to be used on class methods
            and standalone functions"""
        return self.__class__(self._func.__get__(obj, type))

@public
class hook(coroutine):
    """Decorator to mark a function as a hook for cocotb.

    All hooks are run at the beginning of a cocotb test suite, prior to any
    test code being run."""
    def __init__(self):
        pass

    def __call__(self, f):
        super(hook, self).__init__(f)

        def _wrapped_hook(*args, **kwargs):
            try:
                return RunningCoroutine(self._func(*args, **kwargs), self)
            except Exception as e:
                raise raise_error(self, "Hook raised exception:")

        _wrapped_hook.im_hook = True
        _wrapped_hook.name = self._func.__name__
        _wrapped_hook.__name__ = self._func.__name__
        return _wrapped_hook

@public
class test(coroutine):
    """Decorator to mark a function as a test.

    All tests are coroutines.  The test decorator provides
    some common reporting etc., a test timeout and allows
    us to mark tests as expected failures.

    Args:
        timeout (int, optional):
            value representing simulation timeout (not implemented).
        expect_fail (bool, optional):
            Don't mark the result as a failure if the test fails.
        expect_error (bool, optional):
            Don't mark the result as an error if an error is raised.
            This is for cocotb internal regression use.
        skip (bool, optional):
            Don't execute this test as part of the regression.
        stage (int, optional)
            Order tests logically into stages, where multiple tests can share a stage.
    """
    def __init__(self, timeout=None, expect_fail=False, expect_error=False,
                 skip=False, stage=None):
        self.timeout = timeout
        self.expect_fail = expect_fail
        self.expect_error = expect_error
        self.skip = skip
        self.stage = stage

    def __call__(self, f):
        super(test, self).__init__(f)

        def _wrapped_test(*args, **kwargs):
            try:
                return RunningTest(self._func(*args, **kwargs), self)
            except Exception as e:
                raise raise_error(self, "Test raised exception:")

        _wrapped_test.im_test = True    # For auto-regressions
        _wrapped_test.name = self._func.__name__
        _wrapped_test.__name__ = self._func.__name__
        return _wrapped_test
