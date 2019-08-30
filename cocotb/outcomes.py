"""
Inspired by https://github.com/python-trio/outcome

An outcome is similar to the builtin `concurrent.futures.Future`
or `asyncio.Future`, but without being tied to a particular task model.
"""
import abc
import sys

from cocotb import _py_compat


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

        _py_compat.exec_("""def get(self):
            try:
                raise self.error_type, self.error, self.error_tb
            finally:
                del self
        """)
