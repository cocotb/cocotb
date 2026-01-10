# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Utilities for implementors."""

from __future__ import annotations

import sys
import traceback
import types
from collections.abc import Iterable
from enum import Enum, IntEnum
from functools import update_wrapper, wraps
from types import TracebackType
from typing import (
    Any,
    Callable,
    Generic,
    TypeVar,
    cast,
    overload,
)

if sys.version_info >= (3, 10):
    from typing import Concatenate, ParamSpec, TypeAlias

    Params = ParamSpec("Params")

else:
    # hack to make 3.9 happy
    Params = TypeVar("Params")

ExceptionTuple: TypeAlias = tuple[type[BaseException], BaseException, TracebackType]


@overload
def remove_traceback_frames(
    tb_or_exc: ExceptionTuple, frame_names: list[str]
) -> ExceptionTuple: ...


@overload
def remove_traceback_frames(
    tb_or_exc: BaseException, frame_names: list[str]
) -> BaseException: ...


@overload
def remove_traceback_frames(
    tb_or_exc: TracebackType, frame_names: list[str]
) -> TracebackType: ...


def remove_traceback_frames(
    tb_or_exc: ExceptionTuple | BaseException | TracebackType,
    frame_names: list[str],
) -> ExceptionTuple | BaseException | TracebackType:
    """
    Strip leading frames from a traceback

    Args:
        tb_or_exc:
            Object to strip frames from. If an exception is passed, creates
            a copy of the exception with a new shorter traceback. If a tuple
            from `sys.exc_info` is passed, returns the same tuple with the
            traceback shortened
        frame_names:
            Names of the frames to strip, which must be present at the top of the Traceback or Exception.

    Returns:
        Traceback or Exception passed to the function with the *frame_names* stripped out.
    """
    # self-invoking overloads
    if isinstance(tb_or_exc, BaseException):
        exc: BaseException = tb_or_exc
        return exc.with_traceback(
            remove_traceback_frames(
                cast("TracebackType", exc.__traceback__), frame_names
            )
        )
    elif isinstance(tb_or_exc, tuple):
        exc_type, exc_value, exc_tb = tb_or_exc
        exc_tb = remove_traceback_frames(exc_tb, frame_names)
        return exc_type, exc_value, exc_tb
    # base case
    else:
        tb: TracebackType = tb_or_exc
        for frame_name in frame_names:
            # the assert and cast are there assuming the frame_names being removed are correct
            assert tb.tb_frame.f_code.co_name == frame_name
            tb = cast("TracebackType", tb.tb_next)
        return tb


def walk_coro_stack(
    coro: types.CoroutineType[Any, Any, Any],
) -> Iterable[tuple[types.FrameType, int]]:
    """Walk down the coroutine stack, starting at *coro*.

    Args:
        coro: The :class:`coroutine` object to traverse.

    Yields:
        Frame and line number of each frame in the coroutine.
    """
    c: types.CoroutineType[Any, Any, Any] | None = coro
    while c is not None:
        try:
            f = c.cr_frame
        except AttributeError:
            break
        else:
            c = c.cr_await
        if f is not None:
            yield (f, f.f_lineno)


def extract_coro_stack(
    coro: types.CoroutineType[Any, Any, Any], limit: int | None = None
) -> traceback.StackSummary:
    r"""Create a list of pre-processed entries from the coroutine stack.

    This is based on :func:`traceback.extract_tb`.

    If *limit* is omitted or ``None``, all entries are extracted.
    The list is a :class:`traceback.StackSummary` object, and
    each entry in the list is a :class:`traceback.FrameSummary` object
    containing attributes ``filename``, ``lineno``, ``name``, and ``line``
    representing the information that is usually printed for a stack
    trace. The line is a string with leading and trailing
    whitespace stripped; if the source is not available it is ``None``.

    Args:
        coro: The :class:`coroutine` object from which to extract a stack.
        level: The maximum number of frames from *coro*\ s stack to extract.

    Returns:
        The stack of *coro*.
    """
    return traceback.StackSummary.extract(walk_coro_stack(coro), limit=limit)


EnumT = TypeVar("EnumT", bound=Enum)


class DocEnum(Enum):
    """Like :class:`enum.Enum`, but allows documenting enum values.

    Documentation for enum members can be optionally added by setting enum values to a tuple of the intended value and the docstring.
    This adds the provided docstring to the ``__doc__`` field of the enum value.

    .. code-block:: python

        class MyEnum(DocEnum):
            \"\"\"Class documentation\"\"\"

            VALUE1 = 1, "Value documentation"
            VALUE2 = 2  # no documentation

    Taken from :ref:`this StackOverflow answer <https://stackoverflow.com/questions/50473951/how-can-i-attach-documentation-to-members-of-a-python-enum/50473952#50473952>`
    by :ref:`Eric Wieser <https://stackoverflow.com/users/102441/eric>`,
    as recommended by the ``enum_tools`` documentation.
    """

    def __new__(cls: type[EnumT], value: object, doc: str | None = None) -> EnumT:
        # super().__new__() assumes the value is already an enum value
        # so we side step that and create a raw object and fill in _value_
        self = object.__new__(cls)
        self._value_ = value
        if doc is not None:
            self.__doc__ = doc
        return self


IntEnumT = TypeVar("IntEnumT", bound=IntEnum)


class DocIntEnum(IntEnum):
    """Like DocEnum but for :class:`IntEnum` enum types."""

    def __new__(cls: type[IntEnumT], value: int, doc: str | None = None) -> IntEnumT:
        self = int.__new__(cls, value)
        self._value_ = value
        if doc is not None:
            self.__doc__ = doc
        return self


ResultT = TypeVar("ResultT")
InstanceT = TypeVar("InstanceT")


class cached_method(Generic[InstanceT, Params, ResultT]):
    def __init__(
        self, method: Callable[Concatenate[InstanceT, Params], ResultT]
    ) -> None:
        self._method = method
        update_wrapper(self, method)

    @overload
    def __get__(
        self, instance: None, objtype: object = None
    ) -> Callable[Concatenate[InstanceT, Params], ResultT]: ...

    @overload
    def __get__(
        self, instance: InstanceT, objtype: object = None
    ) -> Callable[Params, ResultT]: ...

    def __get__(
        self, instance: None | InstanceT, objtype: object = None
    ) -> Callable[Concatenate[InstanceT, Params], ResultT] | Callable[Params, ResultT]:
        if instance is None:
            return self

        cache: dict[
            tuple[tuple[object, ...], tuple[tuple[str, object], ...]], ResultT
        ] = {}

        @wraps(self._method)
        def lookup(*args: Params.args, **kwargs: Params.kwargs) -> ResultT:
            key = (args, tuple(kwargs.items()))
            try:
                return cache[key]
            except KeyError:
                res = self._method(instance, *args, **kwargs)
                cache[key] = res
                return res

        lookup.cache = cache  # type: ignore[attr-defined]

        setattr(instance, self._method.__name__, lookup)
        return lookup

    def __call__(
        self, instance: InstanceT, *args: Params.args, **kwargs: Params.kwargs
    ) -> ResultT:
        func = getattr(instance, self._method.__name__)
        return func(*args, **kwargs)


class cached_no_args_method(Generic[InstanceT, ResultT]):
    def __init__(self, method: Callable[[InstanceT], ResultT]) -> None:
        self._method = method
        update_wrapper(self, method)

    @overload
    def __get__(
        self, instance: None, objtype: object = None
    ) -> Callable[[InstanceT], ResultT]: ...

    @overload
    def __get__(
        self, instance: InstanceT, objtype: object = None
    ) -> Callable[[], ResultT]: ...

    def __get__(
        self, instance: None | InstanceT, objtype: object = None
    ) -> Callable[[InstanceT], ResultT] | Callable[[], ResultT]:
        if instance is None:
            return self

        res = self._method(instance)

        @wraps(self._method)
        def lookup() -> ResultT:
            return res

        setattr(instance, self._method.__name__, lookup)
        return lookup

    def __call__(self, instance: InstanceT) -> ResultT:
        func = getattr(instance, self._method.__name__)
        return func()


T = TypeVar("T")


def singleton(orig_cls: type[T]) -> type[T]:
    """Class decorator which turns a type into a Singleton type."""
    orig_new = orig_cls.__new__
    orig_init = orig_cls.__init__
    instance = None

    @wraps(orig_cls.__new__)
    def __new__(cls: type[T], *args: object, **kwargs: object) -> T:
        nonlocal instance
        if instance is None:
            instance = orig_new(cls, *args, **kwargs)
            orig_init(instance, *args, **kwargs)
        return instance

    @wraps(orig_cls.__init__)
    def __init__(self: T, *args: object, **kwargs: object) -> None:
        pass

    # I'd like to get rid of type ignoring "assignment", but I'm not sure how to convince
    # mypy that the new function definitions are compatible with the old.
    orig_cls.__new__ = __new__  # type: ignore[method-assign, assignment]
    orig_cls.__init__ = __init__  # type: ignore[method-assign, assignment]
    return orig_cls


def pointer_str(obj: object) -> str:
    """Get the memory address of *obj* as used in :meth:`object.__repr__`.

    This is equivalent to ``sprintf("%p", id(obj))``, but Python does not
    support ``%p``.
    """
    full_repr = object.__repr__(obj)  # gives "<{type} object at {address}>"
    return full_repr.rsplit(" ", 1)[1][:-1]


def safe_divide(a: float, b: float) -> float:
    """Used when computing time ratios to ensure no exception is raised if either time is 0."""
    try:
        return a / b
    except ZeroDivisionError:
        if a == 0:
            return float("nan")
        else:
            return float("inf")
