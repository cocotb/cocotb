''' Copyright (c) 2013 Potential Ventures Ltd
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd nor the
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

import sys
import time
import logging
import traceback

import cocotb
from cocotb.log import SimLog
from cocotb.triggers import Join
from cocotb.result import TestComplete, TestError, TestFailure, TestSuccess


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
        To ensure that a coroutine has completed before we fire any triggers that
        are blocked waiting for the coroutine to end, we create a subclass exception
        that the Scheduler catches and the callbacks are attached here.
    """
    def __init__(self, text="", callback=None):
        StopIteration.__init__(self, text)
        self.callback = callback

    def __call__(self):
        if self.callback is not None: self.callback()


class RunningCoroutine(object):
    """Per instance wrapper around an function to turn it into a coroutine


        Provides the following:

            coro.join() creates a Trigger that will fire when this coroutine completes

            coro.kill() will destroy a coroutine instance (and cause any Join triggers to fire
    """
    def __init__(self, inst, parent):
        self.__name__ = "%s" % inst.__name__
        self.log = SimLog("cocotb.coroutine.%s" % self.__name__, id(self))
        self._coro = inst
        self._finished = False
        self._callbacks = []
        self._parent = parent
        self.__doc__ = parent._func.__doc__
        self.module = parent._func.__module__
        self.funcname = parent._func.__name__

        if not hasattr(self._coro, "send"):
            self.log.error("%s isn't a value coroutine! Did you use the yield keyword?"
                % self.__name__)
            raise CoroutineComplete(callback=self._finished_cb)

    def __iter__(self):
        return self

    def __str__(self):
        return str(self.__name__)

    def send(self, value):
        try:
            return self._coro.send(value)
        except TestComplete as e:
            self.log.info(str(e))
            raise
        except StopIteration:
            raise CoroutineComplete(callback=self._finished_cb)

    def throw(self, exc):
        return self._coro.throw(exc)

    def close(self):
        return self._coro.close()

    def kill(self):
        """Kill a coroutine"""
        self.log.debug("kill() called on coroutine")
        cocotb.scheduler.schedule_remove(self, self._finished_cb)

    def _finished_cb(self):
        """Called when the coroutine completes.
            Allows us to mark the coroutine as finished so that boolean testing works.
            Also call any callbacks, usually the result of coroutine.join()"""
        self._finished = True
        self.log.debug("Coroutine finished calling pending callbacks (%d pending)" % len(self._callbacks))
        for cb in self._callbacks:
            cb()

    def join(self):
        """Return a trigger that will fire when the wrapped coroutine exits"""
        return Join(self)

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
            logging.Handler.__init__(self, level=logging.ERROR)

        def handle(self, record):
            self.fn(self.format(record))


    def __init__(self, inst, parent):
        self.error_messages = []
        RunningCoroutine.__init__(self, inst, parent)
        self.started = False
        self.start_time = 0
        self.expect_fail = parent.expect_fail

        self.handler = RunningTest.ErrorLogHandler(self._handle_error_message)
        cocotb.log.addHandler(self.handler)

    def send(self, value):
        if not self.started:
            self.error_messages = []
            self.log.info("Starting test: \"%s\"\nDescription: %s" % (self.funcname, self.__doc__))
            self.start_time = time.time()
            self.started = True

        try:
            self.log.debug("Sending trigger %s" % (str(value)))
            return self._coro.send(value)
        except TestComplete as e:
            self.log.info(str(e))
            e.stderr.write("\n".join(self.error_messages))
            raise
        except StopIteration:
            raise TestSuccess()

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

    def __call__(self, *args, **kwargs):
        try:
            return RunningCoroutine(self._func(*args, **kwargs), self)
        except Exception as e:
            traceback.print_exc()
            result = TestError(str(e))
            traceback.print_exc(file=result.stderr)
            raise result

    def __get__(self, obj, type=None):
        """Permit the decorator to be used on class methods
            and standalone functions"""
        return self.__class__(self._func.__get__(obj, type))

    def __iter__(self): return self

    def __str__(self):
        return str(self._func.__name__)

@public
class test(coroutine):
    """Decorator to mark a fucntion as a test

    All tests are coroutines.  The test decorator provides
    some common reporting etc, a test timeout and allows
    us to mark tests as expected failures.
    """
    def __init__(self, timeout=None, expect_fail=False):
        self.timeout = timeout
        self.expect_fail = expect_fail

    def __call__(self, f):
        super(test, self).__init__(f)

        def _wrapped_test(*args, **kwargs):
            try:
                return RunningTest(self._func(*args, **kwargs), self)
            except Exception as e:
                traceback.print_exc()
                result = TestError(str(e))
                traceback.print_exc(file=result.stderr)
                raise result

        _wrapped_test.im_test = True    # For auto-regressions
        _wrapped_test.name = self._func.__name__
        return _wrapped_test
