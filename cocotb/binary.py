#!/usr/bin/env python

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

import os
import random
import re
import warnings

_RESOLVE_TO_0 = "-lL"
_RESOLVE_TO_1 = "hH"
_RESOLVE_TO_CHOICE = "xXzZuUwW"
resolve_x_to = os.getenv("COCOTB_RESOLVE_X", "VALUE_ERROR")


class _ResolveTable(dict):
    """Translation table class for resolving binary strings.

    For use with :func:`str.translate()`, which indexes into table with Unicode ordinals.
    """

    def __init__(self):
        self.update({ord("0"): ord("0"), ord("1"): ord("1")})
        self.update({ord(k): ord("0") for k in _RESOLVE_TO_0})
        self.update({ord(k): ord("1") for k in _RESOLVE_TO_1})

        # Do not resolve if resolve_x_to is not set to one of the supported values
        def no_resolve(key):
            return key

        self.resolve_x = no_resolve

        if resolve_x_to == "VALUE_ERROR":

            def resolve_error(key):
                raise ValueError(
                    "Unresolvable bit in binary string: '{}'".format(chr(key))
                )

            self.resolve_x = resolve_error
        elif resolve_x_to == "ZEROS":
            self.update({ord(k): ord("0") for k in _RESOLVE_TO_CHOICE})
        elif resolve_x_to == "ONES":
            self.update({ord(k): ord("1") for k in _RESOLVE_TO_CHOICE})
        elif resolve_x_to == "RANDOM":

            def resolve_random(key):
                # convert to correct Unicode ordinal:
                # ord('0') = 48
                # ord('1') = 49
                return random.getrandbits(1) + 48

            self.resolve_x = resolve_random

        self._resolve_to_choice = {ord(c) for c in _RESOLVE_TO_CHOICE}

    def __missing__(self, key):
        if key in self._resolve_to_choice:
            return self.resolve_x(key)
        else:
            return key


_resolve_table = _ResolveTable()


def resolve(string):
    return string.translate(_resolve_table)


def _clog2(val):
    if val < 0:
        raise ValueError("_clog2 can't take a negative")
    exp = 0
    while True:
        if (1 << exp) >= val:
            return exp
        exp += 1


class BinaryRepresentation:  # noqa
    UNSIGNED = 0  #: Unsigned format
    SIGNED_MAGNITUDE = 1  #: Sign and magnitude format
    TWOS_COMPLEMENT = 2  #: Two's complement format


class BinaryValue:
    """Representation of values in binary format.

    The underlying value can be set or accessed using these aliasing attributes:

        - :attr:`BinaryValue.integer` is an integer
        - :attr:`BinaryValue.signed_integer` is a signed integer
        - :attr:`BinaryValue.binstr` is a string of ``01xXzZ``
        - :attr:`BinaryValue.buff` is a binary buffer of bytes
        - :attr:`BinaryValue.value` is an integer **deprecated**

    For example:

    >>> vec = BinaryValue()
    >>> vec.integer = 42
    >>> print(vec.binstr)
    101010
    >>> print(vec.buff)
    b'*'

    """

    _permitted_chars = _RESOLVE_TO_0 + _RESOLVE_TO_1 + _RESOLVE_TO_CHOICE + "01"  # noqa

    def __init__(
        self,
        value=None,
        n_bits=None,
        bigEndian=True,
        binaryRepresentation=BinaryRepresentation.UNSIGNED,
        bits=None,
    ):
        """
        Args:
            value (str or int or long, optional): Value to assign to the bus.
            n_bits (int, optional): Number of bits to use for the underlying
                binary representation.
            bigEndian (bool, optional): Interpret the binary as big-endian
                when converting to/from a string buffer.
            binaryRepresentation (BinaryRepresentation): The representation
                of the binary value
                (one of :any:`UNSIGNED`, :any:`SIGNED_MAGNITUDE`, :any:`TWOS_COMPLEMENT`).
                Defaults to unsigned representation.
            bits (int, optional): Deprecated: Compatibility wrapper for :attr:`n_bits`.
        """
        self._str = ""
        self.big_endian = bigEndian
        self.binaryRepresentation = binaryRepresentation

        # bits is the deprecated name for n_bits, allow its use for
        # backward-compat reasons.
        if bits is not None and n_bits is not None:
            raise TypeError("You cannot use n_bits and bits at the same time.")
        if bits is not None:
            warnings.warn(
                "The bits argument to BinaryValue has been renamed to n_bits",
                DeprecationWarning,
                stacklevel=2,
            )
            n_bits = bits

        self._n_bits = n_bits

        self._convert_to = self._convert_to_map[self.binaryRepresentation].__get__(
            self, self.__class__
        )

        self._convert_from = self._convert_from_map[self.binaryRepresentation].__get__(
            self, self.__class__
        )

        if value is not None:
            self.assign(value)

    def assign(self, value):
        """Decides how best to assign the value to the vector.

        Picks from the type of its argument whether to set :attr:`integer`,
        :attr:`binstr`, or :attr:`buff`.

        Args:
            value (str or int or bytes): The value to assign.

        .. versionchanged:: 1.4

            This no longer falls back to setting :attr:`buff` if a :class:`str`
            containing any characters that aren't ``0``, ``1``, ``X`` or ``Z``
            is used, since :attr:`buff` now accepts only :class:`bytes`. Instead,
            an error is raised.
        """
        if isinstance(value, int):
            self.integer = value
        elif isinstance(value, str):
            self.binstr = value
        elif isinstance(value, bytes):
            self.buff = value
        else:
            raise TypeError(
                "value must be int, str, or bytes, not {!r}".format(
                    type(value).__qualname__
                )
            )

    def _convert_to_unsigned(self, x):
        if x == 0:
            return self._adjust_unsigned("")
        x = bin(x)
        if x[0] == "-":
            raise ValueError(
                "Attempt to assigned negative number to unsigned " "BinaryValue"
            )
        return self._adjust_unsigned(x[2:])

    def _convert_to_signed_mag(self, x):
        if x == 0:
            return self._adjust_unsigned("")
        x = bin(x)
        if x[0] == "-":
            binstr = self._adjust_signed_mag("1" + x[3:])
        else:
            binstr = self._adjust_signed_mag("0" + x[2:])
        if self.big_endian:
            binstr = binstr[::-1]
        return binstr

    def _convert_to_twos_comp(self, x):
        if x < 0:
            binstr = bin(2 ** (_clog2(abs(x)) + 1) + x)[2:]
            binstr = self._adjust_twos_comp(binstr)
        elif x == 0:
            binstr = self._adjust_twos_comp("")
        else:
            binstr = self._adjust_twos_comp("0" + bin(x)[2:])
        if self.big_endian:
            binstr = binstr[::-1]
        return binstr

    def _convert_from_unsigned(self, x):
        if not len(x):
            return 0
        return int(x.translate(_resolve_table), 2)

    def _convert_from_signed_mag(self, x):
        if not len(x):
            return 0
        rv = int(self._str[1:].translate(_resolve_table), 2)
        if self._str[0] == "1":
            rv = rv * -1
        return rv

    def _convert_from_twos_comp(self, x):
        if not len(x):
            return 0
        if x[0] == "1":
            binstr = x[1:]
            binstr = self._invert(binstr)
            rv = int(binstr, 2) + 1
            rv = rv * -1
        else:
            rv = int(x.translate(_resolve_table), 2)
        return rv

    _convert_to_map = {
        BinaryRepresentation.UNSIGNED: _convert_to_unsigned,
        BinaryRepresentation.SIGNED_MAGNITUDE: _convert_to_signed_mag,
        BinaryRepresentation.TWOS_COMPLEMENT: _convert_to_twos_comp,
    }

    _convert_from_map = {
        BinaryRepresentation.UNSIGNED: _convert_from_unsigned,
        BinaryRepresentation.SIGNED_MAGNITUDE: _convert_from_signed_mag,
        BinaryRepresentation.TWOS_COMPLEMENT: _convert_from_twos_comp,
    }

    _invert_table = str.maketrans({"0": "1", "1": "0"})

    def _invert(self, x):
        return x.translate(self._invert_table)

    def _adjust_unsigned(self, x):
        if self._n_bits is None:
            return x
        l = len(x)
        if l <= self._n_bits:
            if self.big_endian:
                rv = x + "0" * (self._n_bits - l)
            else:
                rv = "0" * (self._n_bits - l) + x
        elif l > self._n_bits:
            if self.big_endian:
                rv = x[l - self._n_bits :]
            else:
                rv = x[: l - self._n_bits]
            warnings.warn(
                "{}-bit value requested, truncating value {!r} ({} bits) to {!r}".format(
                    self._n_bits, x, l, rv
                ),
                category=RuntimeWarning,
                stacklevel=3,
            )
        return rv

    def _adjust_signed_mag(self, x):
        """Pad/truncate the bit string to the correct length."""
        if self._n_bits is None:
            return x
        l = len(x)
        if l < self._n_bits:
            if self.big_endian:
                rv = x[:-1] + "0" * (self._n_bits - 1 - l)
                rv = rv + x[-1]
            else:
                rv = "0" * (self._n_bits - 1 - l) + x[1:]
                rv = x[0] + rv
        elif l > self._n_bits:
            if self.big_endian:
                rv = x[l - self._n_bits :]
            else:
                rv = x[: -(l - self._n_bits)]
            warnings.warn(
                "{}-bit value requested, truncating value {!r} ({} bits) to {!r}".format(
                    self._n_bits, x, l, rv
                ),
                category=RuntimeWarning,
                stacklevel=3,
            )
        else:
            rv = x
        return rv

    def _adjust_twos_comp(self, x):
        if self._n_bits is None:
            return x
        l = len(x)
        if l == 0:
            rv = x
        elif l < self._n_bits:
            if self.big_endian:
                rv = x + x[-1] * (self._n_bits - l)
            else:
                rv = x[0] * (self._n_bits - l) + x
        elif l > self._n_bits:
            if self.big_endian:
                rv = x[l - self._n_bits :]
            else:
                rv = x[: -(l - self._n_bits)]
            warnings.warn(
                "{}-bit value requested, truncating value {!r} ({} bits) to {!r}".format(
                    self._n_bits, x, l, rv
                ),
                category=RuntimeWarning,
                stacklevel=3,
            )
        else:
            rv = x
        return rv

    @property
    def integer(self):
        """The integer representation of the underlying vector."""
        return self._convert_from(self._str)

    @integer.setter
    def integer(self, val):
        self._str = self._convert_to(val)

    @property
    def value(self):
        """Integer access to the value. **deprecated**"""
        return self.integer

    @value.setter
    def value(self, val):
        self.integer = val

    get_value = value.fget
    set_value = value.fset

    @property
    def signed_integer(self):
        """The signed integer representation of the underlying vector."""
        ival = int(self._str.translate(_resolve_table), 2)
        bits = len(self._str)
        signbit = 1 << (bits - 1)
        if (ival & signbit) == 0:
            return ival
        else:
            return -1 * (1 + (int(~ival) & (signbit - 1)))

    @signed_integer.setter
    def signed_integer(self, val):
        self.integer = val

    get_value_signed = signed_integer.fget

    @property
    def is_resolvable(self) -> bool:
        """
        Return whether the value contains only resolvable (i.e. no "unknown") bits.

        By default the values ``X``, ``Z``, ``U`` and ``W`` are considered unresolvable.
        This can be configured with :envvar:`COCOTB_RESOLVE_X`.

        This is similar to the SystemVerilog Assertion ``$isunknown`` system function
        or the VHDL function ``is_x`` (with an inverted meaning).
        """
        return not any(char in self._str for char in _RESOLVE_TO_CHOICE)

    @property
    def buff(self) -> bytes:
        r"""The value as a binary string buffer.

        >>> BinaryValue("01000001" + "00101111").buff == b"\x41\x2F"
        True

        .. versionchanged:: 1.4
            This changed from :class:`str` to :class:`bytes`.
            Note that for older versions used with Python 2 these types were
            indistinguishable.
        """
        bits = self._str.translate(_resolve_table)

        if len(bits) % 8:
            bits = "0" * (8 - len(bits) % 8) + bits

        buff = []
        while bits:
            byte = bits[:8]
            bits = bits[8:]
            val = int(byte, 2)
            if self.big_endian:
                buff += [val]
            else:
                buff = [val] + buff
        return bytes(buff)

    @buff.setter
    def buff(self, val: bytes):
        if not self.big_endian:
            val = reversed(val)
        self._str = "".join([format(char, "08b") for char in val])
        self._adjust()

    def _adjust(self):
        """Pad/truncate the bit string to the correct length."""
        if self._n_bits is None:
            return
        l = len(self._str)
        if l < self._n_bits:
            if self.big_endian:
                self._str = self._str + "0" * (self._n_bits - l)
            else:
                self._str = "0" * (self._n_bits - l) + self._str
        elif l > self._n_bits:
            rv = self._str[l - self._n_bits :]
            warnings.warn(
                "{}-bit value requested, truncating value {!r} ({} bits) to {!r}".format(
                    self._n_bits, self._str, l, rv
                ),
                category=RuntimeWarning,
                stacklevel=3,
            )
            self._str = rv

    get_buff = buff.fget
    set_buff = buff.fset

    @property
    def binstr(self):
        """The binary representation stored as a string of ``0``, ``1``, and possibly ``x``, ``z``, and other states."""
        return self._str

    _non_permitted_regex = re.compile(f"[^{_permitted_chars}]")

    @binstr.setter
    def binstr(self, string):
        match = self._non_permitted_regex.search(string)
        if match:
            raise ValueError(
                "Attempting to assign character %s to a %s"
                % (match.group(), self.__class__.__name__)
            )
        self._str = string
        self._adjust()

    get_binstr = binstr.fget
    set_binstr = binstr.fset

    def _set_trusted_binstr(self, string):
        self._str = string

    @property
    def n_bits(self):
        """The number of bits of the binary value."""
        return self._n_bits

    def hex(self):
        try:
            return hex(self.integer)
        except Exception:
            return hex(int(self.binstr, 2))

    def __le__(self, other):
        self.assign(other)

    def __str__(self):
        return self.binstr

    def __repr__(self):
        return self.__str__()

    def __bool__(self):
        """Provide boolean testing of a :attr:`binstr`.

        >>> val = BinaryValue("0000")
        >>> if val: print("True")
        ... else:   print("False")
        False
        >>> val.integer = 42
        >>> if val: print("True")
        ... else:   print("False")
        True

        """
        for char in self._str:
            if char == "1":
                return True
        return False

    def __eq__(self, other):
        if isinstance(other, BinaryValue):
            other = other.value
        return self.value == other

    def __ne__(self, other):
        if isinstance(other, BinaryValue):
            other = other.value
        return self.value != other

    def __int__(self):
        return self.integer

    def __long__(self):
        return self.integer

    def __add__(self, other):
        return self.integer + int(other)

    def __iadd__(self, other):
        self.integer = self.integer + int(other)
        return self

    def __radd__(self, other):
        return self.integer + other

    def __sub__(self, other):
        return self.integer - int(other)

    def __isub__(self, other):
        self.integer = self.integer - int(other)
        return self

    def __rsub__(self, other):
        return other - self.integer

    def __mul__(self, other):
        return self.integer * int(other)

    def __imul__(self, other):
        self.integer = self.integer * int(other)
        return self

    def __rmul__(self, other):
        return self.integer * other

    def __floordiv__(self, other):
        return self.integer // int(other)

    def __ifloordiv__(self, other):
        self.integer = self.__floordiv__(other)
        return self

    def __rfloordiv__(self, other):
        return other // self.integer

    def __divmod__(self, other):
        return (self.integer // other, self.integer % other)

    def __rdivmod__(self, other):
        return other // self.integer

    def __mod__(self, other):
        return self.integer % int(other)

    def __imod__(self, other):
        self.integer = self.integer % int(other)
        return self

    def __rmod__(self, other):
        return other % self.integer

    def __pow__(self, other, modulo=None):
        return pow(self.integer, other)

    def __ipow__(self, other):
        self.integer = pow(self.integer, other)
        return self

    def __rpow__(self, other):
        return pow(other, self.integer)

    def __lshift__(self, other):
        return int(self) << int(other)

    def __ilshift__(self, other):
        """Preserves X values"""
        self.binstr = self.binstr[other:] + self.binstr[:other]
        return self

    def __rlshift__(self, other):
        return other << self.integer

    def __rshift__(self, other):
        return int(self) >> int(other)

    def __irshift__(self, other):
        """Preserves X values"""
        self.binstr = self.binstr[-other:] + self.binstr[:-other]
        return self

    def __rrshift__(self, other):
        return other >> self.integer

    def __and__(self, other):
        return self.integer & other

    def __iand__(self, other):
        self.integer &= other
        return self

    def __rand__(self, other):
        return self.integer & other

    def __xor__(self, other):
        return self.integer ^ other

    def __ixor__(self, other):
        self.integer ^= other
        return self

    def __rxor__(self, other):
        return self.__xor__(other)

    def __or__(self, other):
        return self.integer | other

    def __ior__(self, other):
        self.integer |= other
        return self

    def __ror__(self, other):
        return self.__or__(other)

    def __div__(self, other):
        return self.integer / other

    def __idiv__(self, other):
        self.integer /= other
        return self

    def __rdiv__(self, other):
        return other / self.integer

    def __neg__(self):
        return -self.integer

    def __pos__(self):
        return +self.integer

    def __abs__(self):
        return abs(self.integer)

    def __invert__(self):
        """Preserves X values"""
        return self._invert(self.binstr)

    def __oct__(self):
        return oct(self.integer)

    def __hex__(self):
        return hex(self.integer)

    def __index__(self):
        return self.integer

    def __len__(self):
        return len(self.binstr)

    def __getitem__(self, key):
        """BinaryValue uses Verilog/VHDL style slices as opposed to Python
        style"""
        if isinstance(key, slice):
            first, second = key.start, key.stop
            if self.big_endian:
                if first < 0 or second < 0:
                    raise IndexError("BinaryValue does not support negative " "indices")
                if second > self._n_bits - 1:
                    raise IndexError("High index greater than number of bits.")
                if first > second:
                    raise IndexError(
                        "Big Endian indices must be specified " "low to high"
                    )
                _binstr = self.binstr[first : (second + 1)]
            else:
                if first < 0 or second < 0:
                    raise IndexError("BinaryValue does not support negative " "indices")
                if first > self._n_bits - 1:
                    raise IndexError("High index greater than number of bits.")
                if second > first:
                    raise IndexError(
                        "Litte Endian indices must be specified " "high to low"
                    )
                high = self._n_bits - second
                low = self._n_bits - 1 - first
                _binstr = self.binstr[low:high]
        else:
            index = key
            if index > self._n_bits - 1:
                raise IndexError("Index greater than number of bits.")
            if self.big_endian:
                _binstr = self.binstr[index]
            else:
                _binstr = self.binstr[self._n_bits - 1 - index]
        rv = BinaryValue(
            n_bits=len(_binstr),
            bigEndian=self.big_endian,
            binaryRepresentation=self.binaryRepresentation,
        )
        rv.binstr = _binstr
        return rv

    def __setitem__(self, key, val):
        """BinaryValue uses Verilog/VHDL style slices as opposed to Python style."""
        if not isinstance(val, str) and not isinstance(val, int):
            raise TypeError("BinaryValue slices only accept string or integer values")

        # convert integer to string
        if isinstance(val, int):
            if isinstance(key, slice):
                num_slice_bits = abs(key.start - key.stop) + 1
            else:
                num_slice_bits = 1
            if val < 0:
                raise ValueError("Integer must be positive")
            if val >= 2**num_slice_bits:
                raise ValueError(
                    "Integer is too large for the specified slice " "length"
                )
            val = "{:0{width}b}".format(val, width=num_slice_bits)

        if isinstance(key, slice):
            first, second = key.start, key.stop

            if self.big_endian:
                if first < 0 or second < 0:
                    raise IndexError("BinaryValue does not support negative " "indices")
                if second > self._n_bits - 1:
                    raise IndexError("High index greater than number of bits.")
                if first > second:
                    raise IndexError(
                        "Big Endian indices must be specified " "low to high"
                    )
                if len(val) > (second + 1 - first):
                    raise ValueError("String length must be equal to slice " "length")
                slice_1 = self.binstr[:first]
                slice_2 = self.binstr[second + 1 :]
                self.binstr = slice_1 + val + slice_2
            else:
                if first < 0 or second < 0:
                    raise IndexError("BinaryValue does not support negative " "indices")
                if first > self._n_bits - 1:
                    raise IndexError("High index greater than number of bits.")
                if second > first:
                    raise IndexError(
                        "Litte Endian indices must be specified " "high to low"
                    )
                high = self._n_bits - second
                low = self._n_bits - 1 - first
                if len(val) > (high - low):
                    raise ValueError("String length must be equal to slice " "length")
                slice_1 = self.binstr[:low]
                slice_2 = self.binstr[high:]
                self.binstr = slice_1 + val + slice_2
        else:
            if len(val) != 1:
                raise ValueError("String length must be equal to slice " "length")
            index = key
            if index > self._n_bits - 1:
                raise IndexError("Index greater than number of bits.")
            if self.big_endian:
                self.binstr = self.binstr[:index] + val + self.binstr[index + 1 :]
            else:
                self.binstr = (
                    self.binstr[0 : self._n_bits - index - 1]
                    + val
                    + self.binstr[self._n_bits - index : self._n_bits]
                )


if __name__ == "__main__":
    import doctest

    doctest.testmod()
