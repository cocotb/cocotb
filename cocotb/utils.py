from __future__ import print_function

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
import math
import os
import sys
import weakref
import functools
import warnings

if "COCOTB_SIM" in os.environ:
    import simulator
    _LOG_SIM_PRECISION = simulator.get_precision()  # request once and cache
else:
    simulator = None
    _LOG_SIM_PRECISION = -15

# This is six.integer_types
if sys.version_info.major >= 3:
    integer_types = (int,)
else:
    integer_types = (int, long)  # noqa


def get_python_integer_types():
    warnings.warn(
        "This is an internal cocotb function, use six.integer_types instead",
        DeprecationWarning)
    return integer_types


# Simulator helper functions
def get_sim_time(units=None):
    """Retrieves the simulation time from the simulator.

    Args:
        units (str or None, optional): String specifying the units of the result
            (one of ``None``, ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``).
            ``None`` will return the raw simulation time.

    Returns:
        The simulation time in the specified units.
    """
    timeh, timel = simulator.get_sim_time()

    result = (timeh << 32 | timel)

    if units is not None:
        result = get_time_from_sim_steps(result, units)

    return result

def get_time_from_sim_steps(steps, units):
    """Calculates simulation time in the specified *units* from the *steps* based
    on the simulator precision.

    Args:
        steps (int): Number of simulation steps.
        units (str): String specifying the units of the result
            (one of ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``).

    Returns:
        The simulation time in the specified units.
    """
    result = steps * (10.0**(_LOG_SIM_PRECISION - _get_log_time_scale(units)))

    return result

def get_sim_steps(time, units=None):
    """Calculates the number of simulation time steps for a given amount of *time*.

    Args:
        time (int or float):  The value to convert to simulation time steps.
        units (str or None, optional):  String specifying the units of the result
            (one of ``None``, ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``).
            ``None`` means time is already in simulation time steps.

    Returns:
        int: The number of simulation time steps.

    Raises:
        :exc:`ValueError`: If given *time* cannot be represented by simulator precision.
    """
    result = time
    if units is not None:
        result = result * (10.0**(_get_log_time_scale(units) - _LOG_SIM_PRECISION))

    err = int(result) - math.ceil(result)

    if err:
        raise ValueError("Unable to accurately represent {0}({1}) with the "
                         "simulator precision of 1e{2}".format(
                             time, units, _LOG_SIM_PRECISION))

    return int(result)

def _get_log_time_scale(units):
    """Retrieves the ``log10()`` of the scale factor for a given time unit.

    Args:
        units (str): String specifying the units
            (one of ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``).

    Returns:
        The the ``log10()`` of the scale factor for the time unit.
    """
    scale = {
        'fs' :    -15,
        'ps' :    -12,
        'ns' :     -9,
        'us' :     -6,
        'ms' :     -3,
        'sec':      0}

    units_lwr = units.lower()
    if units_lwr not in scale:
        raise ValueError("Invalid unit ({0}) provided".format(units))
    else:
        return scale[units_lwr]

# Ctypes helper functions


def pack(ctypes_obj):
    """Convert a :mod:`ctypes` structure into a Python string.

    Args:
        ctypes_obj (ctypes.Structure): The ctypes structure to convert to a string.

    Returns:
        New Python string containing the bytes from memory holding *ctypes_obj*.
    """
    return ctypes.string_at(ctypes.addressof(ctypes_obj),
                            ctypes.sizeof(ctypes_obj))


def unpack(ctypes_obj, string, bytes=None):
    """Unpack a Python string into a :mod:`ctypes` structure.

    If the length of *string* is not the correct size for the memory
    footprint of the ctypes structure then the *bytes* keyword argument 
    must be used.

    Args:
        ctypes_obj (ctypes.Structure): The ctypes structure to pack into.
        string (str):  String to copy over the ctypes_obj memory space.
        bytes (int, optional): Number of bytes to copy. 
            Defaults to ``None``, meaning the length of *string* is used.

    Raises:
        :exc:`ValueError`: If length of *string* and size of *ctypes_obj*
            are not equal.
        :exc:`MemoryError`: If *bytes* is longer than size of *ctypes_obj*.
    """
    if bytes is None:
        if len(string) != ctypes.sizeof(ctypes_obj):
            raise ValueError("Attempt to unpack a string of size %d into a \
                struct of size %d" % (len(string), ctypes.sizeof(ctypes_obj)))
        bytes = len(string)

    if bytes > ctypes.sizeof(ctypes_obj):
        raise MemoryError("Attempt to unpack %d bytes over an object \
                        of size %d" % (bytes, ctypes.sizeof(ctypes_obj)))

    ctypes.memmove(ctypes.addressof(ctypes_obj), string, bytes)


import cocotb.ANSI as ANSI


def _sane_color(x):
    r = ""
    for i in x:
        j = ord(i)
        if (j < 32) or (j >= 127):
            r += "."
        else:
            r += i
    return r


def hexdump(x):
    """Hexdump a buffer.

    Args:
        x: Object that supports conversion via the ``str`` built-in.

    Returns:
        A string containing the hexdump.

    Example:

    .. code-block:: python

        print(hexdump('this somewhat long string'))

    .. code-block:: none

        0000   74 68 69 73 20 73 6F 6D 65 77 68 61 74 20 6C 6F   this somewhat lo
        0010   6E 67 20 73 74 72 69 6E 67                        ng string
    """
    # adapted from scapy.utils.hexdump
    rs = ""
    x = str(x)
    l = len(x)
    i = 0
    while i < l:
        rs += "%04x   " % i
        for j in range(16):
            if i + j < l:
                rs += "%02X " % ord(x[i + j])
            else:
                rs += "   "
            if j % 16 == 7:
                rs += ""
        rs += "  "
        rs += _sane_color(x[i:i + 16]) + "\n"
        i += 16
    return rs


def hexdiffs(x, y):
    """Return a diff string showing differences between two binary strings.

    Args:
        x: Object that supports conversion via the ``str`` built-in.
        y: Object that supports conversion via the ``str`` built-in.

    Example:

    .. code-block:: python

        print(hexdiffs('this short thing', 'this also short'))

    .. code-block:: none

        0000      746869732073686F 7274207468696E67 this short thing
             0000 7468697320616C73 6F  2073686F7274 this also  short

    """
    # adapted from scapy.utils.hexdiff

    def sane(x):
        r = ""
        for i in x:
            j = ord(i)
            if (j < 32) or (j >= 127):
                r = r + "."
            else:
                r = r + i
        return r

    def highlight(string, colour=ANSI.COLOR_HILITE_HEXDIFF_DEFAULT):
        """Highlight only with ANSI output if it's requested and we are not in a GUI."""
        
        want_ansi = os.getenv("COCOTB_ANSI_OUTPUT") and not os.getenv("GUI")
        if want_ansi is None:
            want_ansi = sys.stdout.isatty()  # default to ANSI for TTYs
        else:
            want_ansi = want_ansi == '1'

        if want_ansi:
            return colour + string + ANSI.COLOR_DEFAULT
        else:
            return string

    rs = ""

    x = str(x)[::-1]
    y = str(y)[::-1]
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
            d[i, j] = min((d[i-1, j-1][0] + SUBST*(x[i] != y[j]), (i-1, j-1)),
                          (d[i - 1, j][0] + INSERT, (i - 1, j)),
                          (d[i, j - 1][0] + INSERT, (i, j - 1)))

    backtrackx = []
    backtracky = []
    i = len(x) - 1
    j = len(y) - 1
    while not (i == j == -1):
        i2, j2 = d[i, j][1]
        backtrackx.append(x[i2+1:i+1])
        backtracky.append(y[j2+1:j+1])
        i, j = i2, j2

    x = y = i = 0
    colorize = { 0: lambda x: x,  # noqa
                -1: lambda x: x,  # noqa
                 1: lambda x: x}  # noqa

    dox = 1
    doy = 0
    l = len(backtrackx)
    while i < l:
        separate = 0
        linex = backtrackx[i:i+16]
        liney = backtracky[i:i+16]
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
                    if linex[j] != liney[j]:
                        rs += highlight("%02X" % ord(line[j]),
                                        colour=ANSI.COLOR_HILITE_HEXDIFF_2)
                    else:
                        rs += "%02X" % ord(line[j])
                    if linex[j] == liney[j]:
                        cl += highlight(_sane_color(line[j]),
                                        colour=ANSI.COLOR_HILITE_HEXDIFF_3)
                    else:
                        cl += highlight(sane(line[j]),
                                        colour=ANSI.COLOR_HILITE_HEXDIFF_4)
                else:
                    rs += "  "
                    cl += " "
            else:
                rs += "   "
            if j == 7:
                rs += " "

        rs += " " + cl + '\n'

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


# This is essentially six.exec_
if sys.version_info.major == 3:
    # this has to not be a syntax error in py2
    import builtins
    exec_ = getattr(builtins, 'exec')
else:
    # this has to not be a syntax error in py3
    def exec_(_code_, _globs_=None, _locs_=None):
        """Execute code in a namespace."""
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec("""exec _code_ in _globs_, _locs_""")


# this is six.with_metaclass, with a clearer docstring
def with_metaclass(meta, *bases):
    """This provides:

    .. code-block:: python

        class Foo(with_metaclass(Meta, Base1, Base2)): pass

    which is a unifying syntax for:

    .. code-block:: python

        # python 3
        class Foo(Base1, Base2, metaclass=Meta): pass

        # python 2
        class Foo(Base1, Base2):
            __metaclass__ = Meta
    """
    # This requires a bit of explanation: the basic idea is to make a dummy
    # metaclass for one level of class instantiation that replaces itself with
    # the actual metaclass.
    class metaclass(type):

        def __new__(cls, name, this_bases, d):
            return meta(name, bases, d)

        @classmethod
        def __prepare__(cls, name, this_bases):
            return meta.__prepare__(name, bases)
    return type.__new__(metaclass, 'temporary_class', (), {})


# this is six.raise_from
if sys.version_info[:2] == (3, 2):
    exec_("""def raise_from(value, from_value):
    try:
        if from_value is None:
            raise value
        raise value from from_value
    finally:
        value = None
    """)
elif sys.version_info[:2] > (3, 2):
    exec_("""def raise_from(value, from_value):
    try:
        raise value from from_value
    finally:
        value = None
    """)
else:
    def raise_from(value, from_value):
        raise value


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
        # Once we drop python 2, we can implement a default like the following,
        # which will work in 99% of cases:
        # return tuple(inspect.Signature(cls).bind(*args, **kwargs).arguments.items())
        raise NotImplementedError

    def __call__(cls, *args, **kwargs):
        key = cls.__singleton_key__(*args, **kwargs)
        try:
            return cls.__instances[key]
        except KeyError:
            # construct the object as normal
            self = super(ParametrizedSingleton, cls).__call__(*args, **kwargs)
            cls.__instances[key] = self
            return self


# backport of Python 3.7's contextlib.nullcontext
class nullcontext(object):
    """Context manager that does no additional processing.
    Used as a stand-in for a normal context manager, when a particular
    block of code is only sometimes used with a normal context manager:

    >>> cm = optional_cm if condition else nullcontext()
    >>> with cm:
    >>>     # Perform operation, using optional_cm if condition is True
    """

    def __init__(self, enter_result=None):
        self.enter_result = enter_result

    def __enter__(self):
        return self.enter_result

    def __exit__(self, *excinfo):
        pass


def reject_remaining_kwargs(name, kwargs):
    """
    Helper function to emulate python 3 keyword-only arguments.

    Use as::

        def func(x1, **kwargs):
            a = kwargs.pop('a', 1)
            b = kwargs.pop('b', 2)
            reject_remaining_kwargs('func', kwargs)
            ...

    To emulate the Python 3 syntax::

        def func(x1, *, a=1, b=2):
            ...
    """
    if kwargs:
        # match the error message to what python 3 produces
        bad_arg = next(iter(kwargs))
        raise TypeError(
            '{}() got an unexpected keyword argument {!r}'.format(name, bad_arg)
        )


class lazy_property(object):
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
        setattr(obj, self.fget.__name__, value)
        return value


if __name__ == "__main__":
    import random
    a = ""
    for char in range(random.randint(250, 500)):
        a += chr(random.randint(0, 255))
    b = a
    for error in range(random.randint(2, 9)):
        offset = random.randint(0, len(a))
        b = b[:offset] + chr(random.randint(0, 255)) + b[offset+1:]

    diff = hexdiffs(a, b)
    print(diff)

    space = '\n' + (" " * 20)
    print(space.join(diff.split('\n')))
