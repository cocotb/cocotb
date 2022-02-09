"""
Inspired by https://github.com/python-trio/outcome

An outcome is similar to the builtin `concurrent.futures.Future`
or `asyncio.Future`, but without being tied to a particular task model.
"""
import abc

from cocotb.utils import remove_traceback_frames


def capture(fn, *args, **kwargs):
    """Obtain an `Outcome` representing the result of a function call"""
    try:
        return Value(fn(*args, **kwargs))
    except BaseException as e:
        e = remove_traceback_frames(e, ["capture"])
        return Error(e)


class Outcome(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def send(self, gen):
        """Send or throw this outcome into a generator"""

    @abc.abstractmethod
    def get(self, gen):
        """Get the value of this outcome, or throw its exception"""


class Value(Outcome):
    def __init__(self, value):
        self.value = value

    def send(self, gen):
        return gen.send(self.value)

    def get(self):
        return self.value

    def __repr__(self):
        return f"Value({self.value!r})"


class Error(Outcome):
    def __init__(self, error):
        self.error = error

    def send(self, gen):
        return gen.throw(self.error)

    def get(self):
        raise self.error

    def __repr__(self):
        return f"Error({self.error!r})"
