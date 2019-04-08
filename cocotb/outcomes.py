"""
Inspired by https://github.com/python-trio/outcome

An outcome is similar to the builtin `concurrent.futures.Future`
or `asyncio.Future`, but without being tied to a particular task model.
"""
import abc

from cocotb.utils import reraise

# https://stackoverflow.com/a/38668373
# Backport of abc.ABC, compatible with Python 2 and 3
abc_ABC = abc.ABCMeta('ABC', (object,), {'__slots__': ()})


def capture(fn, *args, **kwargs):
    """ Obtain an `Outcome` representing the result of a function call """
    try:
        return Value(fn(*args, **kwargs))
    except BaseException as e:
        return Error(e)


class Outcome(abc_ABC):
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


class Error(Outcome):
    def __init__(self, *exc_info):
        self.exc_info = exc_info

    def send(self, gen):
        return gen.throw(*self.exc_info)

    def get(self):
        reraise(*self.exc_info)

    def __repr__(self):
        return "Error({!r})".format(self.exc_info[1])
