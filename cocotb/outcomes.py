"""
Inspired by https://github.com/python-trio/outcome

An outcome is similar to the builtin `concurrent.futures.Future`
or `asyncio.Future`, but without being tied to a particular task model.
"""
import abc
import copy
import sys

from cocotb import _py_compat
from cocotb.utils import remove_traceback_frames


def capture(fn, *args, **kwargs):
    """ Obtain an `Outcome` representing the result of a function call """
    try:
        return Value(fn(*args, **kwargs))
    except BaseException as e:
        return Error(e)


class Outcome(_py_compat.abc_ABC):
    @abc.abstractmethod
    def send(self, gen):
        """ Send or throw this outcome into a generator """

    @abc.abstractmethod
    def get(self, gen):
        """ Get the value of this outcome, or throw its exception """


class Value(Outcome):
    def __init__(self, value):
        self.value = value

    def send(self, gen):
        return gen.send(self.value)

    def get(self):
        return self.value

    def __repr__(self):
        return "Value({!r})".format(self.value)


class _ErrorBase(Outcome):
    def __init__(self, error):
        self.error = error

    def __repr__(self):
        return "Error({!r})".format(self.error)


if sys.version_info.major >= 3:
    class Error(_ErrorBase):
        def send(self, gen):
            return gen.throw(self.error)

        def get(self):
            raise self.error

        # Once we drop Python 2, this can be inlined at the caller, it's here
        # just for convenience writing code that works on both versions
        def without_frames(self, frame_names):
            return Error(remove_traceback_frames(self.error, frame_names))

else:
    # Python 2 needs extra work to preserve tracebacks
    class Error(_ErrorBase):
        def __init__(self, error):
            super(Error, self).__init__(error)
            # guess the traceback
            t, e, tb = sys.exc_info()
            if e is error:
                self.error_type = t
                self.error_tb = tb
            else:
                # no traceback - this might be a new exception
                self.error_type = type(error)
                self.error_tb = None

        def send(self, gen):
            return gen.throw(self.error_type, self.error, self.error_tb)

        def without_frames(self, frame_names):
            ret = copy.copy(self)
            ret.error_tb = remove_traceback_frames(ret.error_tb, frame_names)
            return ret

        # We need a wrapper function to ensure the traceback is the same
        # depth as on Python 3 - `raise type, val, tb` is not included in the
        # stack trace in Python 2.
        _py_compat.exec_("""def _get(self):
            try:
                raise self.error_type, self.error, self.error_tb
            finally:
                del self
        """)

        def get(self):
            return self._get()
