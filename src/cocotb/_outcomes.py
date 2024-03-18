"""
Inspired by https://github.com/python-trio/outcome

An outcome is similar to the builtin `concurrent.futures.Future`
or `asyncio.Future`, but without being tied to a particular task model.
"""

import abc
from typing import Any, Callable, Coroutine

from cocotb.utils import remove_traceback_frames


def capture(fn: Callable[..., Any], *args, **kwargs):
    """Obtain an `Outcome` representing the result of a function call"""
    try:
        return Value(fn(*args, **kwargs))
    except BaseException as e:
        e = remove_traceback_frames(e, ["capture"])
        return Error(e)


class Outcome(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def send(self, coro: Coroutine) -> Any:
        """Send or throw this outcome into a coroutine"""

    @abc.abstractmethod
    def get(self) -> Any:
        """Get the value of this outcome, or throw its exception"""


class Value(Outcome):
    def __init__(self, value: Any):
        self.value = value

    def send(self, coro: Coroutine) -> Any:
        return coro.send(self.value)

    def get(self) -> Any:
        return self.value

    def __repr__(self) -> str:
        return f"Value({self.value!r})"


class Error(Outcome):
    def __init__(self, error: BaseException):
        self.error = error

    def send(self, coro: Coroutine) -> Any:
        return coro.throw(self.error)

    def get(self) -> Any:
        raise self.error

    def __repr__(self) -> str:
        return f"Error({self.error!r})"
