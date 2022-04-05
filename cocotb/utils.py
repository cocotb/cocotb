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
import ctypes
import functools
import inspect
import math
import os
import sys
import traceback
import warnings
import weakref
from decimal import Decimal
from numbers import Real
from typing import Union

import cocotb.ANSI as ANSI
from cocotb import simulator


def _get_simulator_precision():
    # cache and replace this function
    precision = simulator.get_precision()
    global _get_simulator_precision
    _get_simulator_precision = precision.__int__
    return _get_simulator_precision()


def get_python_integer_types():
    warnings.warn(
        "This is an internal cocotb function, use six.integer_types instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return (int,)


# Simulator helper functions
def get_sim_time(units: str = "step") -> int:
    """Retrieves the simulation time from the simulator.

    Args:
        units: String specifying the units of the result
            (one of ``'step'``, ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``).
            ``'step'`` will return the raw simulation time.

            .. deprecated:: 1.6.0
                Using ``None`` as the *units* argument is deprecated, use ``'step'`` instead.

    Returns:
        The simulation time in the specified units.

    .. versionchanged:: 1.6.0
        Support ``'step'`` as the the *units* argument to mean "simulator time step".
    """
    timeh, timel = simulator.get_sim_time()

    result = timeh << 32 | timel

    if units not in (None, "step"):
        result = get_time_from_sim_steps(result, units)
    if units is None:
        warnings.warn(
            'Using units=None is deprecated, use units="step" instead.',
            DeprecationWarning,
            stacklevel=2,
        )

    return result


def _ldexp10(frac, exp):
    """Like math.ldexp, but base 10"""
    # using * or / separately prevents rounding errors if `frac` is a
    # high-precision type
    if exp > 0:
        return frac * (10**exp)
    else:
        return frac / (10**-exp)


def get_time_from_sim_steps(steps: int, units: str) -> int:
    """Calculates simulation time in the specified *units* from the *steps* based
    on the simulator precision.

    Args:
        steps: Number of simulation steps.
        units: String specifying the units of the result
            (one of ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``).

    Returns:
        The simulation time in the specified units.
    """
    return _ldexp10(steps, _get_simulator_precision() - _get_log_time_scale(units))


def get_sim_steps(
    time: Union[Real, Decimal], units: str = "step", *, round_mode: str = "error"
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
    if units not in (None, "step"):
        result = _ldexp10(time, _get_log_time_scale(units) - _get_simulator_precision())
    else:
        result = time
    if units is None:
        warnings.warn(
            'Using units=None is deprecated, use units="step" instead.',
            DeprecationWarning,
            stacklevel=2,
        )
        units = "step"  # don't propagate deprecated value

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


def _get_log_time_scale(units):
    """Retrieves the ``log10()`` of the scale factor for a given time unit.

    Args:
        units (str): String specifying the units
            (one of ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``).

    Returns:
        The ``log10()`` of the scale factor for the time unit.
    """
    scale = {"fs": -15, "ps": -12, "ns": -9, "us": -6, "ms": -3, "sec": 0}

    units_lwr = units.lower()
    if units_lwr not in scale:
        raise ValueError(f"Invalid unit ({units}) provided")
    else:
        return scale[units_lwr]


# Ctypes helper functions


def pack(ctypes_obj):
    """Convert a :mod:`ctypes` structure into a Python string.

    Args:
        ctypes_obj (ctypes.Structure): The :mod:`ctypes` structure to convert to a string.

    Returns:
        New Python string containing the bytes from memory holding *ctypes_obj*.

    .. deprecated:: 1.5
        This function is deprecated, use ``bytes(ctypes_obj)`` instead.
    """
    warnings.warn(
        "This function is deprecated and will be removed, use ``bytes(ctypes_obj)`` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return ctypes.string_at(ctypes.addressof(ctypes_obj), ctypes.sizeof(ctypes_obj))


def unpack(ctypes_obj, string, bytes=None):
    """Unpack a Python string into a :mod:`ctypes` structure.

    If the length of *string* is not the correct size for the memory
    footprint of the :mod:`ctypes` structure then the *bytes* keyword argument
    must be used.

    Args:
        ctypes_obj (ctypes.Structure): The :mod:`ctypes` structure to pack into.
        string (str):  String to copy over the *ctypes_obj* memory space.
        bytes (int, optional): Number of bytes to copy.
            Defaults to ``None``, meaning the length of *string* is used.

    Raises:
        :exc:`ValueError`: If length of *string* and size of *ctypes_obj*
            are not equal.
        :exc:`MemoryError`: If *bytes* is longer than size of *ctypes_obj*.

    .. deprecated:: 1.5
        Converting bytes to a ctypes object should be done with :meth:`~ctypes._CData.from_buffer_copy`.
        If you need to assign bytes into an *existing* ctypes object, use ``memoryview(ctypes_obj).cast('B')[:bytes] = string``,
        see :class:`memoryview` for details.
    """
    warnings.warn(
        "This function is being removed, use ``memoryview(ctypes_obj).cast('B')[:bytes] = string`` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    if bytes is None:
        if len(string) != ctypes.sizeof(ctypes_obj):
            raise ValueError(
                "Attempt to unpack a string of size %d into a \
                struct of size %d"
                % (len(string), ctypes.sizeof(ctypes_obj))
            )
        bytes = len(string)

    if bytes > ctypes.sizeof(ctypes_obj):
        raise MemoryError(
            "Attempt to unpack %d bytes over an object \
                        of size %d"
            % (bytes, ctypes.sizeof(ctypes_obj))
        )

    ctypes.memmove(ctypes.addressof(ctypes_obj), string, bytes)


# A note on the use of latin1 in the deprecations below:
# Latin1 is the only encoding `e` that satisfies
# `all(chr(x).encode(e) == bytes([x]) for x in range(255))`
# Our use of `ord` and `chr` throughout other bits of code make this the most
# compatible choice of encoding. Under this convention, old code can be upgraded
# by changing "binary" strings from `"\x12\x34"` to `b"\x12\x34"`.


def _sane(x: bytes) -> str:
    r = ""
    for j in x:
        if (j < 32) or (j >= 127):
            r += "."
        else:
            r += chr(j)
    return r


def hexdump(x: bytes) -> str:
    """Hexdump a buffer.

    Args:
        x: Object that supports conversion to :class:`bytes`.

    Returns:
        A string containing the hexdump.

    .. deprecated:: 1.4
        Passing a :class:`str` to this function is deprecated, as it
        is not an appropriate type for binary data. Doing so anyway
        will encode the string to ``latin1``.

    .. deprecated:: 1.6.0
        The function will be removed in the next major version.
        Use :func:`scapy.utils.hexdump` instead.

    Example:
        >>> print(hexdump(b'this somewhat long string'))
        0000   74 68 69 73 20 73 6F 6D 65 77 68 61 74 20 6C 6F   this somewhat lo
        0010   6E 67 20 73 74 72 69 6E 67                        ng string
        <BLANKLINE>
    """
    # adapted from scapy.utils.hexdump
    warnings.warn(
        "cocotb.utils.hexdump is deprecated. Use scapy.utils.hexdump instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    rs = ""
    if isinstance(x, str):
        warnings.warn(
            "Passing a string to hexdump is deprecated, pass bytes instead",
            DeprecationWarning,
            stacklevel=2,
        )
        x = x.encode("latin1")
    x = b"%b" % x
    l = len(x)
    i = 0
    while i < l:
        rs += "%04x   " % i
        for j in range(16):
            if i + j < l:
                rs += "%02X " % x[i + j]
            else:
                rs += "   "
            if j % 16 == 7:
                rs += ""
        rs += "  "
        rs += _sane(x[i : i + 16]) + "\n"
        i += 16
    return rs


def hexdiffs(x: bytes, y: bytes) -> str:
    r"""Return a diff string showing differences between two binary strings.

    Args:
        x: Object that supports conversion to :class:`bytes`.
        y: Object that supports conversion to :class:`bytes`.

    .. deprecated:: 1.4
        Passing :class:`str`\ s to this function is deprecated, as it
        is not an appropriate type for binary data. Doing so anyway
        will encode the string to ``latin1``.

    .. deprecated:: 1.6.0
        The function will be removed in the next major version.
        Use :func:`scapy.utils.hexdiff` instead.

    Example:
        >>> print(hexdiffs(b'a', b'b'))
        0000      61                                               a
             0000 62                                               b
        <BLANKLINE>
        >>> print(hexdiffs(b'this short thing', b'this also short'))
        0000      746869732073686F 7274207468696E67 this short thing
             0000 7468697320616C73 6F  2073686F7274 this also  short
        <BLANKLINE>
    """
    # adapted from scapy.utils.hexdiff
    warnings.warn(
        "cocotb.utils.hexdiffs is deprecated. Use scapy.utils.hexdiff instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    def highlight(string: str, colour=ANSI.COLOR_HILITE_HEXDIFF_DEFAULT) -> str:
        """Highlight with ANSI colors if possible/requested and not running in GUI."""

        if want_color_output():
            return colour + string + ANSI.COLOR_DEFAULT
        else:
            return string

    x_is_str = isinstance(x, str)
    y_is_str = isinstance(y, str)
    if x_is_str or y_is_str:
        warnings.warn(
            "Passing strings to hexdiffs is deprecated, pass bytes instead",
            DeprecationWarning,
            stacklevel=2,
        )
    if x_is_str:
        x = x.encode("latin1")
    if y_is_str:
        y = y.encode("latin1")

    rs = ""

    x = (b"%b" % x)[::-1]
    y = (b"%b" % y)[::-1]
    SUBST = 1
    INSERT = 1
    d = {}
    d[-1, -1] = 0, (-1, -1)
    for j in range(len(y)):
        d[-1, j] = d[-1, j - 1][0] + INSERT, (-1, j - 1)
    for i in range(len(x)):
        d[i, -1] = d[i - 1, -1][0] + INSERT, (i - 1, -1)

    for j in range(len(y)):
        for i in range(len(x)):
            d[i, j] = min(
                (d[i - 1, j - 1][0] + SUBST * (x[i] != y[j]), (i - 1, j - 1)),
                (d[i - 1, j][0] + INSERT, (i - 1, j)),
                (d[i, j - 1][0] + INSERT, (i, j - 1)),
            )

    backtrackx = []
    backtracky = []
    i = len(x) - 1
    j = len(y) - 1
    while not (i == j == -1):
        i2, j2 = d[i, j][1]
        backtrackx.append(x[i2 + 1 : i + 1])
        backtracky.append(y[j2 + 1 : j + 1])
        i, j = i2, j2

    x = y = i = 0
    colorize = {0: lambda x: x, -1: lambda x: x, 1: lambda x: x}  # noqa  # noqa  # noqa

    dox = 1
    doy = 0
    l = len(backtrackx)
    while i < l:
        linex = backtrackx[i : i + 16]
        liney = backtracky[i : i + 16]
        xx = sum(len(k) for k in linex)
        yy = sum(len(k) for k in liney)
        if dox and not xx:
            dox = 0
            doy = 1
        if dox and linex == liney:
            doy = 1

        if dox:
            xd = y
            j = 0
            while not linex[j]:
                j += 1
                xd -= 1
            if dox != doy:
                rs += highlight("%04x" % xd) + " "
            else:
                rs += highlight("%04x" % xd, colour=ANSI.COLOR_HILITE_HEXDIFF_1) + " "
            x += xx
            line = linex
        else:
            rs += "    "
        if doy:
            yd = y
            j = 0
            while not liney[j]:
                j += 1
                yd -= 1
            if doy - dox != 0:
                rs += " " + highlight("%04x" % yd)
            else:
                rs += highlight("%04x" % yd, colour=ANSI.COLOR_HILITE_HEXDIFF_1)
            y += yy
            line = liney
        else:
            rs += "    "

        rs += " "

        cl = ""
        for j in range(16):
            if i + j < l:
                if line[j]:
                    (char_j,) = line[j]
                    if linex[j] != liney[j]:
                        rs += highlight(
                            "%02X" % char_j, colour=ANSI.COLOR_HILITE_HEXDIFF_2
                        )
                    else:
                        rs += "%02X" % char_j
                    if linex[j] == liney[j]:
                        cl += highlight(
                            _sane(line[j]), colour=ANSI.COLOR_HILITE_HEXDIFF_3
                        )
                    else:
                        cl += highlight(
                            _sane(line[j]), colour=ANSI.COLOR_HILITE_HEXDIFF_4
                        )
                else:
                    rs += "  "
                    cl += " "
            else:
                rs += "   "
            if j == 7:
                rs += " "

        rs += " " + cl + "\n"

        if doy or not yy:
            doy = 0
            dox = 1
            i += 16
        else:
            if yy:
                dox = 0
                doy = 1
            else:
                i += 16
    return rs


class ParametrizedSingleton(type):
    """A metaclass that allows class construction to reuse an existing instance.

    We use this so that :class:`RisingEdge(sig) <cocotb.triggers.RisingEdge>` and :class:`Join(coroutine) <cocotb.triggers.Join>` always return
    the same instance, rather than creating new copies.
    """

    def __init__(cls, *args, **kwargs):
        # Attach a lookup table to this class.
        # Weak such that if the instance is no longer referenced, it can be
        # collected.
        cls.__instances = weakref.WeakValueDictionary()

    def __singleton_key__(cls, *args, **kwargs):
        """Convert the construction arguments into a normalized representation that
        uniquely identifies this singleton.
        """
        # Could default to something like this, but it would be slow
        # return tuple(inspect.Signature(cls).bind(*args, **kwargs).arguments.items())
        raise NotImplementedError

    def __call__(cls, *args, **kwargs):
        key = cls.__singleton_key__(*args, **kwargs)
        try:
            return cls.__instances[key]
        except KeyError:
            # construct the object as normal
            self = super().__call__(*args, **kwargs)
            cls.__instances[key] = self
            return self

    @property
    def __signature__(cls):
        return inspect.signature(cls.__singleton_key__)


def reject_remaining_kwargs(name, kwargs):
    """
    Helper function to emulate Python 3 keyword-only arguments.

    Use as::

        def func(x1, **kwargs):
            a = kwargs.pop('a', 1)
            b = kwargs.pop('b', 2)
            reject_remaining_kwargs('func', kwargs)
            ...

    To emulate the Python 3 syntax::

        def func(x1, *, a=1, b=2):
            ...

    .. deprecated:: 1.4
        Since the minimum supported Python version is now 3.5, this function
        is not needed.
    """
    warnings.warn(
        "reject_remaining_kwargs is deprecated and will be removed, use "
        "Python 3 keyword-only arguments directly.",
        DeprecationWarning,
        stacklevel=2,
    )
    if kwargs:
        # match the error message to what Python 3 produces
        bad_arg = next(iter(kwargs))
        raise TypeError(f"{name}() got an unexpected keyword argument {bad_arg!r}")


class lazy_property:
    """
    A property that is executed the first time, then cached forever.

    It does this by replacing itself on the instance, which works because
    unlike `@property` it does not define __set__.

    This should be used for expensive members of objects that are not always
    used.
    """

    def __init__(self, fget):
        self.fget = fget

        # copy the getter function's docstring and other attributes
        functools.update_wrapper(self, fget)

    def __get__(self, obj, cls):
        if obj is None:
            return self

        value = self.fget(obj)
        setattr(obj, self.fget.__qualname__, value)
        return value


def want_color_output():
    """Return ``True`` if colored output is possible/requested and not running in GUI.

    Colored output can be explicitly requested by setting :envvar:`COCOTB_ANSI_OUTPUT` to  ``1``.
    """
    want_color = sys.stdout.isatty()  # default to color for TTYs
    if os.getenv("NO_COLOR") is not None:
        want_color = False
    if os.getenv("COCOTB_ANSI_OUTPUT", default="0") == "1":
        want_color = True
    if os.getenv("GUI", default="0") == "1":
        want_color = False
    return want_color


def remove_traceback_frames(tb_or_exc, frame_names):
    """
    Strip leading frames from a traceback

    Args:
        tb_or_exc (Union[traceback, BaseException, exc_info]):
            Object to strip frames from. If an exception is passed, creates
            a copy of the exception with a new shorter traceback. If a tuple
            from `sys.exc_info` is passed, returns the same tuple with the
            traceback shortened
        frame_names (List[str]):
            Names of the frames to strip, which must be present.
    """
    # self-invoking overloads
    if isinstance(tb_or_exc, BaseException):
        exc = tb_or_exc
        return exc.with_traceback(
            remove_traceback_frames(exc.__traceback__, frame_names)
        )
    elif isinstance(tb_or_exc, tuple):
        exc_type, exc_value, exc_tb = tb_or_exc
        exc_tb = remove_traceback_frames(exc_tb, frame_names)
        return exc_type, exc_value, exc_tb
    # base case
    else:
        tb = tb_or_exc
        for frame_name in frame_names:
            assert tb.tb_frame.f_code.co_name == frame_name
            tb = tb.tb_next
        return tb


def walk_coro_stack(coro):
    """Walk down the coroutine stack, starting at *coro*.

    Supports coroutines and generators.
    """
    while coro is not None:
        try:
            f = getattr(coro, "cr_frame")
            coro = coro.cr_await
        except AttributeError:
            try:
                f = getattr(coro, "gi_frame")
                coro = coro.gi_yieldfrom
            except AttributeError:
                f = None
                coro = None
        if f is not None:
            yield (f, f.f_lineno)


def extract_coro_stack(coro, limit=None):
    """Create a list of pre-processed entries from the coroutine stack.

    This is based on :func:`traceback.extract_tb`.

    If *limit* is omitted or ``None``, all entries are extracted.
    The list is a :class:`traceback.StackSummary` object, and
    each entry in the list is a :class:`traceback.FrameSummary` object
    containing attributes ``filename``, ``lineno``, ``name``, and ``line``
    representing the information that is usually printed for a stack
    trace.  The line is a string with leading and trailing
    whitespace stripped; if the source is not available it is ``None``.
    """
    return traceback.StackSummary.extract(walk_coro_stack(coro), limit=limit)
