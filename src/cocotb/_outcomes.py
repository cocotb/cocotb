"""
Inspired by https://github.com/python-trio/outcome

An outcome is similar to the builtin `concurrent.futures.Future`
or `asyncio.Future`, but without being tied to a particular task model.
"""

import abc
from typing import Any, Callable, Coroutine, Generic, TypeVar

from cocotb._utils import remove_traceback_frames

T = TypeVar("T")


def capture(fn: Callable[..., T], *args: Any, **kwargs: Any) -> "Outcome[T]":
    """Obtain an `Outcome` representing the result of a function call"""
    try:
        return Value(fn(*args, **kwargs))
    except BaseException as e:
        e = remove_traceback_frames(e, ["capture"])
        return Error(e)


class Outcome(Generic[T], metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def send(self, coro: Coroutine[Any, T, Any]) -> Any:
        """Send or throw this outcome into a coroutine"""

    @abc.abstractmethod
    def get(self) -> T:
        """Get the value of this outcome, or throw its exception"""


class Value(Outcome[T]):
    def __init__(self, value: T):
        self.value = value

    def send(self, coro: Coroutine[Any, T, Any]) -> Any:
        return coro.send(self.value)

    def get(self) -> T:
        return self.value

    def __repr__(self) -> str:
        return f"Value({self.value!r})"


class Error(Outcome[T]):
    def __init__(self, error: BaseException) -> None:
        self.error = error

    def send(self, coro: Coroutine[Any, T, Any]) -> Any:
        return coro.throw(self.error)

    def get(self) -> T:
        raise self.error

    def __repr__(self) -> str:
        return f"Error({self.error!r})"
