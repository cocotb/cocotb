# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd,
#       SolarFlare Communications Inc nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Collection of handy functions."""

import inspect
import math
import os
import sys
import traceback
import types
import weakref
from abc import ABCMeta
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from functools import lru_cache
from types import TracebackType
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from cocotb import simulator


def _get_simulator_precision() -> int:
    # cache and replace this function
    precision = simulator.get_precision()
    global _get_simulator_precision
    _get_simulator_precision = precision.__int__
    return _get_simulator_precision()


# Simulator helper functions
def get_sim_time(units: str = "step") -> int:
    """Retrieve the simulation time from the simulator.

    Args:
        units: String specifying the units of the result
            (one of ``'step'``, ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``).
            ``'step'`` will return the raw simulation time.

            .. versionchanged:: 2.0
                Passing ``None`` as the *units* argument was removed, use ``'step'`` instead.

    Raises:
        ValueError: If *units* is not a valid unit (see Args section).

    Returns:
        The simulation time in the specified units.

    .. versionchanged:: 1.6.0
        Support ``'step'`` as the the *units* argument to mean "simulator time step".
    """
    timeh, timel = simulator.get_sim_time()

    result = timeh << 32 | timel

    if units != "step":
        result = get_time_from_sim_steps(result, units)

    return result


@overload
def _ldexp10(frac: int, exp: int) -> int: ...


@overload
def _ldexp10(frac: Union[float, Fraction], exp: int) -> float: ...


@overload
def _ldexp10(frac: Decimal, exp: int) -> Decimal: ...


def _ldexp10(frac: Union[float, Fraction, Decimal], exp: int) -> Any:
    """Like :func:`math.ldexp`, but base 10."""
    # using * or / separately prevents rounding errors if `frac` is a
    # high-precision type
    if exp > 0:
        return frac * (10**exp)
    else:
        return frac / (10**-exp)


def get_time_from_sim_steps(steps: int, units: str) -> int:
    """Calculate simulation time in the specified *units* from the *steps* based
    on the simulator precision.

    Args:
        steps: Number of simulation steps.
        units: String specifying the units of the result
            (one of ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``).

    Raises:
        ValueError: If *units* is not a valid unit (see Args section).

    Returns:
        The simulation time in the specified units.
    """
    return _ldexp10(steps, _get_simulator_precision() - _get_log_time_scale(units))


def get_sim_steps(
    time: Union[float, Fraction, Decimal],
    units: str = "step",
    *,
    round_mode: str = "error",
) -> int:
    """Calculates the number of simulation time steps for a given amount of *time*.

    When *round_mode* is ``"error"``, a :exc:`ValueError` is thrown if the value cannot
    be accurately represented in terms of simulator time steps.
    When *round_mode* is ``"round"``, ``"ceil"``, or ``"floor"``, the corresponding
    rounding function from the standard library will be used to round to a simulator
    time step.

    Args:
        time: The value to convert to simulation time steps.
        units: String specifying the units of the result
            (one of ``'step'``, ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``).
            ``'step'`` means *time* is already in simulation time steps.
        round_mode: String specifying how to handle time values that sit between time steps
            (one of ``'error'``, ``'round'``, ``'ceil'``, ``'floor'``).

    Returns:
        The number of simulation time steps.

    Raises:
        ValueError: if the value cannot be represented accurately in terms of simulator
            time steps when *round_mode* is ``"error"``.

    .. versionchanged:: 1.5
        Support ``'step'`` as the *units* argument to mean "simulator time step".

    .. versionchanged:: 1.6
        Support rounding modes.
    """
    result: Union[float, Fraction, Decimal]
    if units != "step":
        result = _ldexp10(time, _get_log_time_scale(units) - _get_simulator_precision())
    else:
        result = time

    if round_mode == "error":
        result_rounded = math.floor(result)
        if result_rounded != result:
            precision = _get_simulator_precision()
            raise ValueError(
                f"Unable to accurately represent {time}({units}) with the simulator precision of 1e{precision}"
            )
    elif round_mode == "ceil":
        result_rounded = math.ceil(result)
    elif round_mode == "round":
        result_rounded = round(result)
    elif round_mode == "floor":
        result_rounded = math.floor(result)
    else:
        raise ValueError(f"Invalid round_mode specifier: {round_mode}")

    return result_rounded


@lru_cache(maxsize=None)
def _get_log_time_scale(units: str) -> int:
    """Retrieves the ``log10()`` of the scale factor for a given time unit.

    Args:
        units: String specifying the units
            (one of ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``).

    Raises:
        ValueError: If *units* is not a valid unit (see Args section).

    Returns:
        The ``log10()`` of the scale factor for the time unit.
    """
    scale = {"fs": -15, "ps": -12, "ns": -9, "us": -6, "ms": -3, "sec": 0}

    units_lwr = units.lower()
    if units_lwr not in scale:
        raise ValueError(f"Invalid unit ({units}) provided")
    else:
        return scale[units_lwr]


class _ParameterizedSingletonMetaclass(ABCMeta):
    """A metaclass that allows class construction to reuse an existing instance.

    We use this so that :class:`RisingEdge(sig) <cocotb.triggers.RisingEdge>` and :class:`Join(coroutine) <cocotb.triggers.Join>` always return
    the same instance, rather than creating new copies.
    """

    __singleton_key__: Callable[..., Any]

    def __init__(
        cls, name: str, bases: Sequence[Type[object]], dct: Dict[str, Any]
    ) -> None:
        # Attach a lookup table to this class.
        # Weak such that if the instance is no longer referenced, it can be
        # collected.
        cls.__instances: weakref.WeakValueDictionary[Any, Any] = (
            weakref.WeakValueDictionary()
        )

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        key = cls.__singleton_key__(*args, **kwargs)
        try:
            return cls.__instances[key]
        except KeyError:
            # construct the object as normal
            self = super().__call__(*args, **kwargs)
            cls.__instances[key] = self
            return self

    @property
    def __signature__(cls) -> inspect.Signature:
        return inspect.signature(cls.__singleton_key__)


@lru_cache(maxsize=None)
def want_color_output() -> bool:
    """Return ``True`` if colored output is possible/requested and not running in GUI.

    Colored output can be explicitly requested in a cocotb-specific way
    by setting :envvar:`COCOTB_ANSI_OUTPUT` to  ``1``.

    Returns: Whether color output is wanted and supported.
    """
    want_color = sys.stdout.isatty()  # default to color for TTYs
    if os.getenv("NO_COLOR") is not None:
        want_color = False
    if os.getenv("COCOTB_ANSI_OUTPUT", default="0") == "1":
        want_color = True
    if os.getenv("GUI", default="0") == "1":
        want_color = False
    return want_color


ExceptionTuple = Tuple[
    Type[BaseException], BaseException, TracebackType
]  # TypeAlias in Python 3.10


@overload
def remove_traceback_frames(
    tb_or_exc: ExceptionTuple, frame_names: List[str]
) -> ExceptionTuple: ...


@overload
def remove_traceback_frames(
    tb_or_exc: BaseException, frame_names: List[str]
) -> BaseException: ...


@overload
def remove_traceback_frames(
    tb_or_exc: TracebackType, frame_names: List[str]
) -> TracebackType: ...


def remove_traceback_frames(
    tb_or_exc: Union[ExceptionTuple, BaseException, TracebackType],
    frame_names: List[str],
) -> Union[ExceptionTuple, BaseException, TracebackType]:
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
            remove_traceback_frames(cast(TracebackType, exc.__traceback__), frame_names)
        )
    elif isinstance(tb_or_exc, tuple):
        exc_type, exc_value, exc_tb = cast(ExceptionTuple, tb_or_exc)
        exc_tb = remove_traceback_frames(exc_tb, frame_names)
        return exc_type, exc_value, exc_tb
    # base case
    else:
        tb: TracebackType = tb_or_exc
        for frame_name in frame_names:
            # the assert and cast are there assuming the frame_names being removed are correct
            assert tb.tb_frame.f_code.co_name == frame_name
            tb = cast(TracebackType, tb.tb_next)
        return tb


def walk_coro_stack(
    coro: "types.CoroutineType[Any, Any, Any]",
) -> Iterable[Tuple[types.FrameType, int]]:
    """Walk down the coroutine stack, starting at *coro*.

    Args:
        coro: The :class:`coroutine` object to traverse.

    Yields:
        Frame and line number of each frame in the coroutine.
    """
    c: Optional[types.CoroutineType[Any, Any, Any]] = coro
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
    coro: "types.CoroutineType[Any, Any, Any]", limit: Optional[int] = None
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

    .. code-block:: python3

        class MyEnum(DocEnum):
            \"\"\"Class documentation\"\"\"

            VALUE1 = 1, "Value documentation"
            VALUE2 = 2  # no documentation

    Taken from :ref:`this StackOverflow answer <https://stackoverflow.com/questions/50473951/how-can-i-attach-documentation-to-members-of-a-python-enum/50473952#50473952>`
    by :ref:`Eric Wieser <https://stackoverflow.com/users/102441/eric>`,
    as recommended by the ``enum_tools`` documentation.
    """

    def __new__(cls: Type[EnumT], value: Any, doc: Optional[str] = None) -> EnumT:
        # super().__new__() assumes the value is already an enum value
        # so we side step that and create a raw object and fill in _value_
        self = object.__new__(cls)
        self._value_ = value
        if doc is not None:
            self.__doc__ = doc
        return self
