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

import logging

import cocotb
from cocotb.triggers import Join


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


class TestComplete(StopIteration):
    """
        Indicate that a test has finished
    """
    def __init__(self, result):
        self.result = result


class coroutine(object):
    """Decorator class that allows us to provide common coroutine mechanisms:

        log methods will will log to cocotb.coroutines.name

        join() method returns an event which will fire when the coroutine exits
    """

    def __init__(self, func):
        self._func = func
        self.__name__ = func.__name__   # FIXME should use functools.wraps?
        self._callbacks = []
        self.log =  logging.getLogger("cocotb.coroutine.%s" % func.__name__)
        self._finished = False

    def __call__(self, *args, **kwargs):
        self._coro = self._func(*args, **kwargs)
        return self

    def __get__(self, obj, type=None):
        """Permit the decorator to be used on class methods
            and standalone functions"""
        return self.__class__(self._func.__get__(obj, type))

    def __iter__(self): return self

    def next(self):
        """FIXME: deprecated by send method?"""
        try:
            return self._coro.next()
        except StopIteration:
            raise CoroutineComplete(callback=self._finished_cb)

    def send(self, value):
        """FIXME: problem here is that we don't let the call stack unwind..."""
        try:
            return self._coro.send(value)
        except StopIteration:
            raise CoroutineComplete(callback=self._finished_cb)

    def throw(self, exc):
        return self._coro.throw(exc)

    def kill(self):
        self.log.warning("kill() called on coroutine")
        self.throw(StopIteration)

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


class test(coroutine):
    """Decorator to mark a fucntion as a test

    All tests are coroutines.  The test decorator provides
    some common reporting etc, a test timeout and allows
    us to mark tests as expected failures.
    """
    def __init__(self, timeout=None, expect_fail=False):
        self.timeout = timeout
        self.expect_fail = expect_fail
        self.started = False

    def __call__(self, f):
        """
        ping

        """
        super(test, self).__init__(f)
        def _wrapped_test(*args, **kwargs):
            super(test, self).__call__(*args, **kwargs)
            return self
        return _wrapped_test


    def send(self, value):
        """FIXME: problem here is that we don't let the call stack unwind..."""
        if not self.started:
            self.log.info("Starting test: \"%s\"\nDescription: %s" % (self.__name__, self._func.__doc__))
            self.started = True
        try:
            self.log.info("sending %s" % (str(value)))
            return self._coro.send(value)
        except StopIteration:
            raise TestComplete(result="Passed")
        except cocotb.TestFailed:
            raise TestComplete(result="Failed")
