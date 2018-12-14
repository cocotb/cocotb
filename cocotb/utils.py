from __future__ import print_function

''' Copyright (c) 2013, 2018 Potential Ventures Ltd
Copyright (c) 2013 SolarFlare Communications Inc
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd,
      SolarFlare Communications Inc nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. '''

"""Collection of handy functions"""

import ctypes
import math
import os
import sys

# Only for in case of simulation, disable for autodocumentation
if "COCOTB_SIM" in os.environ:
    import simulator
    _LOG_SIM_PRECISION = simulator.get_precision() # request once and cache
else:
    simulator = None
    _LOG_SIM_PRECISION = -15

# python2 to python3 helper functions
def get_python_integer_types():
    try:
        isinstance(1, long)
    except NameError:
        return (int,)  # python 3
    else:
        return (int, long)  # python 2

# Simulator helper functions
def get_sim_time(units=None):
    """Retrieves the simulation time from the simulator

    Kwargs:
        units (str):  String specifying the units of the result. (None,'fs','ps','ns','us','ms','sec')
                      None will return the raw simulation time.

    Returns:
        The simulation time in the specified units
    """
    timeh, timel = simulator.get_sim_time()

    result = (timeh << 32 | timel)

    if units is not None:
        result = get_time_from_sim_steps(result, units)

    return result

def get_time_from_sim_steps(steps, units):
    """Calculates simulation time in the specified units from the steps based on the simulator precision.

    Args:
        steps (int):  Number of simulation steps
        units (str):  String specifying the units of the result. ('fs','ps','ns','us','ms','sec')

    Returns:
        The simulation time in the specified units
    """
    result = steps * (10.0**(_LOG_SIM_PRECISION - _get_log_time_scale(units)))

    return result

def get_sim_steps(time, units=None):
    """Calculates the number of Simulation time steps for a given amount of time

    Args:
        time (int/float):  The value to convert to simulation time steps.

    Kwargs:
        units (str):  String specifying the units of the result. (None,'fs','ps','ns','us','ms','sec')
                      None means time is already in simulation time steps.

    Returns:
        The number of simulation time steps
    """
    result = time
    if units is not None:
        result = result * (10.0**(_get_log_time_scale(units) - _LOG_SIM_PRECISION))

    err = int(result) - math.ceil(result)

    if err:
        raise ValueError("Unable to accurately represent {0}({1}) with the simulator precision of 1e{2}".format(time,units,_LOG_SIM_PRECISION))

    return int(result)

def _get_log_time_scale(units):
    """Retrieves the log10() of the scale factor for a given time unit

    Args:
        units (str):  String specifying the units. ('fs','ps','ns','us','ms','sec')

    Returns:
        The the log10() of the scale factor for the time unit
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
    """Convert a ctypes structure into a python string


    Args:
        ctypes_obj (ctypes.Structure): ctypes structure to convert to a string


    Returns:
        New python string containing the bytes from memory holding ctypes_obj
    """
    return ctypes.string_at(ctypes.addressof(ctypes_obj),
                            ctypes.sizeof(ctypes_obj))


def unpack(ctypes_obj, string, bytes=None):
    """Unpack a python string into a ctypes structure

    Args:
        ctypes_obj (ctypes.Structure):  ctypes structure to pack into

        string (str):  String to copy over the ctypes_obj memory space

    Kwargs:
        bytes: Number of bytes to copy

    Raises:
        ValueError, MemoryError

    If the length of the string is not the correct size for the memory
    footprint of the ctypes structure then the bytes keyword argument must
    be used
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
    """Hexdump a buffer"""
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
    """Return a diff string showing differences between 2 binary strings"""
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
        want_ansi = os.getenv("COCOTB_ANSI_OUTPUT")
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
