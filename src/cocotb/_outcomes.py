"""
Inspired by https://github.com/python-trio/outcome

An outcome is similar to the built-in :any:`concurrent.futures.Future`
or :any:`asyncio.Future`, but without being tied to a particular task model.
"""

import abc
from typing import Callable, Generic, TypeVar

from cocotb._py_compat import ParamSpec
from cocotb._utils import remove_traceback_frames

T = TypeVar("T")
P = ParamSpec("P")


def capture(
    fn: "Callable[P, T]", *args: "P.args", **kwargs: "P.kwargs"
) -> "Outcome[T]":
    """Obtain an `Outcome` representing the result of a function call."""
    try:
        return Value(fn(*args, **kwargs))
    except BaseException as e:
        e = remove_traceback_frames(e, ["capture"])
        return Error(e)


class Outcome(Generic[T]):
    @abc.abstractmethod
    def get(self) -> T:
        """Get the value of this outcome, or throw its exception."""


class Value(Outcome[T]):
    def __init__(self, value: T):
        self.value = value

    def get(self) -> T:
        return self.value

    def __repr__(self) -> str:
        return f"Value({self.value!r})"


class Error(Outcome[T]):
    def __init__(self, error: BaseException) -> None:
        self.error = error

    def get(self) -> T:
        raise self.error

    def __repr__(self) -> str:
        return f"Error({self.error!r})"
