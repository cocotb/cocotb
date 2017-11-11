''' Copyright (c) 2013 Potential Ventures Ltd
Copyright (c) 2013 SolarFlare Communications Inc
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd,
      SolarFlare Communications Inc nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. '''
from __future__ import print_function
import sys
import time
import logging
import traceback
import threading
import pdb

from io import StringIO, BytesIO

import cocotb
from cocotb.log import SimLog
from cocotb.triggers import _Join, PythonTrigger, Timer, Event, NullTrigger
from cocotb.result import (TestComplete, TestError, TestFailure, TestSuccess,
                           ReturnValue, create_error)
from cocotb.utils import get_sim_time


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
class CoroutineComplete(StopIteration):
    """
        To ensure that a coroutine has completed before we fire any triggers
        that are blocked waiting for the coroutine to end, we create a subclass
        exception that the Scheduler catches and the callbacks are attached
        here.
    """
    def __init__(self, text="", callback=None):
        StopIteration.__init__(self, text)
        self.callback = callback


class RunningCoroutine(object):
    """Per instance wrapper around an function to turn it into a coroutine


        Provides the following:

            coro.join() creates a Trigger that will fire when this coroutine
            completes

            coro.kill() will destroy a coroutine instance (and cause any Join
            triggers to fire
    """
    def __init__(self, inst, parent):
        if hasattr(inst, "__name__"):
            self.__name__ = "%s" % inst.__name__
            self.log = SimLog("cocotb.coroutine.%s" % self.__name__, id(self))
        else:
            self.log = SimLog("cocotb.coroutine.fail")
        self._coro = inst
        self._finished = False
        self._callbacks = []
        self._join = _Join(self)
        self._parent = parent
        self.__doc__ = parent._func.__doc__
        self.module = parent._func.__module__
        self.funcname = parent._func.__name__
        self.retval = None

        if not hasattr(self._coro, "send"):
            self.log.error("%s isn't a value coroutine! Did you use the yield "
                           "keyword?" % self.funcname)
            raise CoroutineComplete(callback=self._finished_cb)

    def __iter__(self):
        return self

    def __str__(self):
        return str(self.__name__)

    def send(self, value):
        try:
            return self._coro.send(value)
        except TestComplete as e:
            if isinstance(e, TestFailure):
                self.log.warning(str(e))
            raise
        except ReturnValue as e:
            self.retval = e.retval
            self._finished = True
            raise CoroutineComplete(callback=self._finished_cb)
        except StopIteration:
            self._finished = True
            raise CoroutineComplete(callback=self._finished_cb)
        except Exception as e:
            self._finished = True
            raise create_error(self, "Send raised exception: %s" % (str(e)))

    def throw(self, exc):
        return self._coro.throw(exc)

    def close(self):
        return self._coro.close()

    def kill(self):
        """Kill a coroutine"""
        self.log.debug("kill() called on coroutine")
        cocotb.scheduler.unschedule(self)

    def _finished_cb(self):
        """Called when the coroutine completes.
            Allows us to mark the coroutine as finished so that boolean testing
            works.
            Also call any callbacks, usually the result of coroutine.join()"""
        self._finished = True

    def join(self):
        """Return a trigger that will fire when the wrapped coroutine exits"""
        if self._finished:
            return NullTrigger()
        else:
            return self._join

    def __nonzero__(self):
        """Provide boolean testing
            if the coroutine has finished return false
            otherwise return true"""
        return not self._finished


class RunningTest(RunningCoroutine):
    """Add some useful Test functionality to a RunningCoroutine"""

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

        self.handler = RunningTest.ErrorLogHandler(self._handle_error_message)
        cocotb.log.addHandler(self.handler)

    def send(self, value):
        if not self.started:
            self.error_messages = []
            self.log.info("Starting test: \"%s\"\nDescription: %s" %
                          (self.funcname, self.__doc__))
            self.start_time = time.time()
            self.start_sim_time = get_sim_time('ns')
            self.started = True
        try:
            self.log.debug("Sending trigger %s" % (str(value)))
            return self._coro.send(value)
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
            raise create_error(self, "Send raised exception: %s" % (str(e)))

    def _handle_error_message(self, msg):
        self.error_messages.append(msg)


class coroutine(object):
    """Decorator class that allows us to provide common coroutine mechanisms:

        log methods will will log to cocotb.coroutines.name

        join() method returns an event which will fire when the coroutine exits
    """

    def __init__(self, func):
        self._func = func
        self.log = SimLog("cocotb.function.%s" % self._func.__name__, id(self))
        self.__name__ = self._func.__name__

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
    """Decorator class that allows a a function to block

    This allows a function to internally block while
    externally appear to yield

    """
    def __init__(self, func):
        self._func = func
        self.log = SimLog("cocotb.function.%s" % self._func.__name__, id(self))

    def __call__(self, *args, **kwargs):

        @coroutine
        def execute_function(self, event):
            event.result = yield cocotb.coroutine(self._func)(*args, **kwargs)
            event.set()

        self._event = threading.Event()
        self._event.result = None
        coro = cocotb.scheduler.queue(execute_function(self, self._event))
        self._event.wait()

        return self._event.result

    def __get__(self, obj, type=None):
        """Permit the decorator to be used on class methods
            and standalone functions"""
        return self.__class__(self._func.__get__(obj, type))


@function
def unblock_external(bridge):
    yield NullTrigger()
    bridge.set_out()


@public
class test_locker(object):
    def __init__(self):
        self.in_event = None
        self.out_event = Event()
        self.result = None

    def set_in(self):
        self.in_event.set()

    def set_out(self):
        self.out_event.set()


def external(func):
    """Decorator to apply to an external function to enable calling from cocotb

    This currently creates a new execution context for each function that is
    call. Scope for this to be streamlined to a queue in future
    """

    @coroutine
    def wrapped(*args, **kwargs):
        # Start up the thread, this is done in coroutine context
        bridge = test_locker()

        def execute_external(func, _event):
            _event.result = func(*args, **kwargs)
            # Queue a co-routine to
            unblock_external(_event)

        thread = threading.Thread(group=None, target=execute_external,
                                  name=func.__name__ + "thread",
                                  args=([func, bridge]), kwargs={})
        thread.start()

        yield bridge.out_event.wait()

        if bridge.result is not None:
            raise ReturnValue(bridge.result)

    return wrapped


@public
class test(coroutine):
    """Decorator to mark a function as a test

    All tests are coroutines.  The test decorator provides
    some common reporting etc, a test timeout and allows
    us to mark tests as expected failures.

    KWargs:
        timeout: (int)
            value representing simulation timeout (not implemented)
        expect_fail: (bool):
            Don't mark the result as a failure if the test fails
        expect_error: (bool):
            Don't make the result as an error if an error is raised
            This is for cocotb internal regression use
        skip: (bool):
            Don't execute this test as part of the regression
    """
    def __init__(self, timeout=None, expect_fail=False, expect_error=False,
                 skip=False):
        self.timeout = timeout
        self.expect_fail = expect_fail
        self.expect_error = expect_error
        self.skip = skip

    def __call__(self, f):
        super(test, self).__init__(f)

        def _wrapped_test(*args, **kwargs):
            try:
                return RunningTest(self._func(*args, **kwargs), self)
            except Exception as e:
                raise create_error(self, str(e))

        _wrapped_test.im_test = True    # For auto-regressions
        _wrapped_test.name = self._func.__name__
        _wrapped_test.__name__ = self._func.__name__
        return _wrapped_test
