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

from __future__ import print_function
from cocotb.utils import integer_types
from cocotb.log import SimLog

import os
import random
import warnings

resolve_x_to = os.getenv('COCOTB_RESOLVE_X', "VALUE_ERROR")

def resolve(string):
    """Resolve a multi-state binary string to a 2 state binary string

    Resolve other states (e.g. X from VHDL std_logic/Verilog logic) to 0 or 1
    """
    for char in BinaryValue._resolve_to_0:
        string = string.replace(char, "0")
    for char in BinaryValue._resolve_to_1:
        string = string.replace(char, "1")
    for char in BinaryValue._resolve_to_error:
        if resolve_x_to == "VALUE_ERROR" and char in string:
            raise ValueError("Unable to resolve to binary >%s<" % string)
        elif resolve_x_to == "ZEROS":
            string = string.replace(char, "0")
        elif resolve_x_to == "ONES":
            string = string.replace(char, "1")
        elif resolve_x_to == "RANDOM":
            bits = "{0:b}".format(random.getrandbits(1))
            string = string.replace(char, bits)
    return string


def _clog2(val):
    if val < 0:
        raise ValueError("_clog2 can't take a negative")
    exp = 0
    while True:
        if (1 << exp) >= val:
            return exp
        exp += 1


class BinaryRepresentation():  # noqa
    UNSIGNED         = 0  #: Unsigned format
    SIGNED_MAGNITUDE = 1  #: Sign and magnitude format
    TWOS_COMPLEMENT  = 2  #: Two's complement format


class BinaryValue(object):
    """Representation of values in binary format.

    The underlying value can be set or accessed using these aliasing attributes:

        - :attr:`BinaryValue.integer` is an integer
        - :attr:`BinaryValue.signed_integer` is a signed integer
        - :attr:`BinaryValue.binstr` is a string of "01xXzZ"
        - :attr:`BinaryValue.buff` is a binary buffer of bytes
        - :attr:`BinaryValue.value` is an integer **deprecated**

    For example:

    >>> vec = BinaryValue()
    >>> vec.integer = 42
    >>> print(vec.binstr)
    101010
    >>> print(repr(vec.buff))
    '*'

    """
    # Accepted characters and resolution
    _resolve_to_0     = "-lL"  # noqa
    _resolve_to_1     = "hH"  # noqa
    _resolve_to_error = "xXzZuUwW"  # Resolve to a ValueError() since these usually mean something is wrong
    _permitted_chars  = _resolve_to_0 +_resolve_to_1 + _resolve_to_error + "01"  # noqa

    # Class logging member
    _log = SimLog("cocotb.binary.BinaryValue")

    def __init__(self, value=None, n_bits=None, ascendingRange=None,
                 binaryRepresentation=BinaryRepresentation.UNSIGNED,
                 bits=None, bigEndian=None):
        """Args:
            value (str or int or long, optional): Value to assign to the bus.
            n_bits (int, optional): Number of bits to use for the underlying
                binary representation.
            ascendingRange (bool, optional): Interpret the binary string as
                having a big-endian bit order.
            binaryRepresentation (BinaryRepresentation): The representation
                of the binary value
                (one of :any:`UNSIGNED`, :any:`SIGNED_MAGNITUDE`, :any:`TWOS_COMPLEMENT`).
                Defaults to unsigned representation.
            ascending_range (bool, optional): Interpret the binary string bit-order
                as having an ascending range (big-endian bits).
            bits (int, optional): Deprecated: Compatibility wrapper for :attr:`n_bits`.
            bigEndian (bool, optional): Deprecated: Compatibility wrapper for
                :attr:`ascendingRange`.
        """
        # The underlying vector:
        # - Mirrors the representation in HW
        # - This is a Python string of bits
        # - Note that because it is a string, if acending_range is false, indexing (of strings) no
        #   longer provides the expected result (0th index is still the start of the string)
        self._str = ""

        self.binaryRepresentation = binaryRepresentation

        # bigEndian is the deprecated name for ascendingRange, allow its use for
        # backwards-compat reasons.
        if bigEndian is not None and ascendingRange is not None:
            raise TypeError("You cannot use bigEndian and ascendingRange at the same time")
        if bigEndian is not None:
            warnings.warn("The bigEndian argument to BinaryValue has been renamed to ascendingRange",
                          DeprecationWarning, stacklevel=2)
            ascendingRange = bigEndian
        if ascendingRange is None:
            ascendingRange = True  # DEFAULT BIG-ENDIAN
        self.ascending_range = ascendingRange

        # bits is the deprecated name for n_bits, allow its use for
        # backward-compat reasons.
        if bits is not None and n_bits is not None:
            raise TypeError("You cannot use n_bits and bits at the same time.")
        if bits is not None:
            warnings.warn(
                "The bits argument to BinaryValue has been renamed to n_bits",
                DeprecationWarning, stacklevel=2)
            n_bits = bits

        self._n_bits = n_bits

        # Convert integer to string buffer
        self._convert_to = {BinaryRepresentation.UNSIGNED         : self._convert_to_unsigned,
                            BinaryRepresentation.SIGNED_MAGNITUDE : self._convert_to_signed_mag,
                            BinaryRepresentation.TWOS_COMPLEMENT  : self._convert_to_twos_comp}

        # Convert to integer from string buffer
        self._convert_from = {BinaryRepresentation.UNSIGNED         : self._convert_from_unsigned,
                              BinaryRepresentation.SIGNED_MAGNITUDE : self._convert_from_signed_mag,
                              BinaryRepresentation.TWOS_COMPLEMENT  : self._convert_from_twos_comp}

        # Extend/truncate string buffer
        self._adjust = {BinaryRepresentation.UNSIGNED         : self._adjust_unsigned,
                        BinaryRepresentation.SIGNED_MAGNITUDE : self._adjust_signed_mag,
                        BinaryRepresentation.TWOS_COMPLEMENT  : self._adjust_twos_comp}

        if value is not None:
            self.assign(value)

    def assign(self, value):
        """Decides how best to assign the value to the vector.

        We possibly try to be a bit too clever here by first of
        all trying to assign the raw string as a binstring, however
        if the string contains any characters that aren't
        ``0``, ``1``, ``X`` or ``Z``
        then we interpret the string as a binary buffer.

        Args:
            value (str or int or long): The value to assign.
        """
        if isinstance(value, integer_types):
            self.value = value
        elif isinstance(value, str):
            try:
                self.binstr = value
            except ValueError:
                self.buff = value
        else:
            raise TypeError("assign requires a str or int or long, "
                            "got type '{}'".format(type(value)))

    def _convert_to_unsigned(self, x):
        """Convert an unsigned integer to a unsigned binary string"""
        x = bin(x)
        if x[0] == '-':
            raise ValueError('Attempt to assigned negative number to unsigned '
                             'BinaryValue')
        x = x[2:]  # Remove '0b' prefix
        if self.ascending_range:
            x = x[::-1]
        return self._adjust_unsigned(x)

    def _convert_to_signed_mag(self, x):
        """Convert a signed integer to a signed magnitude binary string"""
        x = bin(x)  # Little-endian bit-order
        if x[0] == '-':
            x = '1' + x[3:]  # Attach negative sign
        else:
            x = '0' + x[2:0]  # Attach positive sign
        if self.ascending_range:
            x = x[::-1]  # Convert x to big-endian bit-order
        return self._adjust_signed_mag(x)

    def _convert_to_twos_comp(self, x):
        """Convert a signed integer to a twos complement signed binary string"""
        if x < 0:  # Convert to integer representing unsigned twos complement value
            binstr = bin(2 ** (_clog2(abs(x)) + 1) + x)[2:]
        else:
            binstr = '0' + bin(x)[2:]
        # binstr is little-endian bit-order
        if self.ascending_range:
            binstr = binstr[::-1]
        return self._adjust_twos_comp(binstr)

    def _convert_from_unsigned(self, x):
        """Convert an unsigned binary string to an integer"""
        if self.ascending_range:
            x = x[::-1]  # Python interprets binary strings as little-endian bit-order
        return int(resolve(x), 2)

    def _convert_from_signed_mag(self, x):
        """Convert a signed magnitude binary string to an integer"""
        if self.ascending_range:
            x = x[::-1]  # Python interprets binary strings as little-endian bit-order
        magnitude = int(resolve(x[1:]), 2)
        if x[0] == '1':  # Handle sign bit
            return 0 - magnitude
        return magnitude

    def _convert_from_twos_comp(self, x):
        """Convert a signed twos complement binary string to an integer"""
        if self.ascending_range:
            x = x[::-1]  # Python interprets binary strings as little-endian bit-order
        if x[0] == '1':  # Negative value
            # Conversion = invert and add 1
            binstr = self._invert(x[1:])  # Remove sign and invert
            return 0 - (int(binstr, 2) + 1)
        return int(resolve(x), 2)

    def _invert(self, x):
        """Invert the bits of a bit string"""
        inverted = []
        for bit in x:
            if bit == '0':
                inverted.append('1')
            elif bit == '1':
                inverted.append('0')
            else:
                inverted.append(bit)
        return "".join(inverted)

    def _adjust_unsigned(self, x, n_bits=None):
        """Extend/truncate an unsigned binary string to n_bits length

        If truncation is required, occurs on least significant bits
        Args:
            x (str): Unsigned binary string
            n_bits (int, optional): Size override
        """
        if n_bits is None:
            n_bits = self._n_bits
        if n_bits is None:
            return x
        length = len(x)
        if length <= n_bits:  # Extension with 0s (unsigned)
            if self.ascending_range:
                return x + '0' * (n_bits - length)
            return '0' * (n_bits - length) + x
        else:  # Truncation (l > n_bits)
            self._log.warning("Truncating value to match requested number of bits (%d -> %d)",
                              length, n_bits)
            # Truncate MSBs (standard verilog behaviour)
            if self.ascending_range:
                return x[:n_bits - length]
            return x[length - n_bits:]

    def _adjust_signed_mag(self, x, n_bits=None):
        """Extend/truncate a signed magnitude bit string to n_bits length

        Args:
            x (str): Unsigned binary string
            n_bits (int, optional): Size override
        """
        if n_bits is None:
            n_bits = self._n_bits
        if n_bits is None:
            return x
        length = len(x)
        if length <= n_bits:
            if self.ascending_range:
                # (x without sign) + (padding 0s) + (sign)
                return x[:-1] + '0' * (n_bits - 1 - length) + x[-1]
            # (sign) + (padding 0s) + (x without sign)
            return x[0] + '0' * (n_bits - 1 - length) + x[1:]
        else:  # Truncation (l > n_bits)
            self._log.warning("Truncating value to match requested number of bits (%d -> %d)",
                              length, n_bits)
            # Truncate MSBs (standard verilog behaviour)
            # NOTE: Lose sign data
            if self.ascending_range:
                return x[:n_bits - length]
            return x[length - n_bits:]

    def _adjust_twos_comp(self, x, n_bits=None):
        """Extend/truncate a twos complement bit string to n_bits length

        Args:
            x (str): Unsigned binary string
            n_bits (int, optional): Size override
        """
        if n_bits is None:
            n_bits = self._n_bits
        if n_bits is None:
            return x
        length = len(x)
        if length <= n_bits:  # Sign extension
            if self.ascending_range:
                return x + x[-1] * (n_bits - length)
            return x[0] * (n_bits - length) + x
        else:  # Truncation (l > self._n_bits)
            self._log.warning("Truncating value to match requested number of bits (%d -> %d)",
                              length, n_bits)
            if self.ascending_range:
                return x[:n_bits - length]
            return x[length - n_bits:]

    def get_value(self):
        """Return the integer representation of the underlying vector."""
        return self._convert_from[self.binaryRepresentation](self._str)

    def get_value_signed(self):
        """Return the signed integer representation of the underlying vector. **deprecated**"""
        if self.binaryRepresentation == BinaryRepresentation.UNSIGNED:
            raise ValueError("Attempt to convert unsigned value to signed")
        elif self.binaryRepresentation not in [BinaryRepresentation.SIGNED_MAGNITUDE, BinaryRepresentation.TWOS_COMPLEMENT]:
            raise TypeError("Unrecognised binary representation")
        return self.get_value()

    def set_value(self, integer):
        """Set the integer value"""
        self._str = self._convert_to[self.binaryRepresentation](integer)

    @property
    def is_resolvable(self):
        """Does the value contain any ``X``'s?  Inquiring minds want to know."""
        return not any(char in self._str for char in BinaryValue._resolve_to_error)

    def _get_bytes(self):
        """Get the value as a list of resolved bytes

        The value is resolved and grouped into bytes.
        This returns a big-endian byte-order list of bytes.
        """
        length = len(self._str)
        if length % 8 != 0:
            length = ((length // 8) + 1) * 8  # Round up to nearest byte
        bits = self._adjust[self.binaryRepresentation](resolve(self._str), length)
        byte_strings = (bits[i:i+8] for i in range(0, len(bits), 8))
        if self.ascending_range:
            # Bytes are in correct positions, but within each byte the bit-order is incorrect
            return [int(byte_str[::-1], 2) for byte_str in byte_strings]
        # Bit-order for each byte is correct, but bytes are in little-endian byte order
        return [int(byte_str, 2) for byte_str in byte_strings][::-1]

    def get_buff(self):
        """Attribute :attr:`buff` represents the value as a resolved byte string buffer.

        >>> "0100000100101111".buff == "\x41\x2F"
        True

        Returns a big-endian byte-order bytestring (where each byte has little-endian bit order)
        """
        return "".join(chr(byte) for byte in self._get_bytes())

    def get_hex_buff(self):
        """Get the value as a resolved hex string buffer

        >>> "0100000100101111".buff == "412F"
        True

        Returns a big-endian byte-order hex string (where each byte has little-endian bit order)
        """
        return "".join(hex(byte)[2:0] for byte in self._get_bytes()).upper()

    def set_buff(self, buff):
        """Set the value using a byte string

        Takes a big-endian byte-order bit string.
        (Within each byte, bit-order is little-endian)
        """
        converted_buffer = ("{:08b}".format(ord(char)) for char in buff)
        if self.ascending_range:
            # Need to swap bit-order within each byte
            converted_buffer = "".join(binstr[::-1] for binstr in converted_buffer)
        else:
            # Need to swap byte-order for each byte
            converted_buffer = "".join(list(converted_buffer)[::-1])
        self._str = self._adjust[self.binaryRepresentation](converted_buffer)

    def get_binstr(self):
        """Attribute :attr:`binstr` is the unresolved binary representation stored
        as a string of ``1`` and ``0``."""
        return self._str

    def set_binstr(self, string):
        """Set the internal binary string"""
        for char in string:
            if char not in BinaryValue._permitted_chars:
                raise ValueError("Attempting to assign character %s to a %s" %
                                 (char, self.__class__.__name__))
        self._str = self._adjust[self.binaryRepresentation](string)

    value = property(get_value, set_value, None,
                     "Integer access to the value. **deprecated**")
    integer = property(get_value, set_value, None,
                       "The integer representation of the underlying vector.")
    signed_integer = property(get_value_signed, set_value, None,
                              "The signed integer representation of the underlying vector. **deprecated**")
    buff = property(get_buff, set_buff, None,
                    "Access to the value as a buffer.")
    binstr = property(get_binstr, set_binstr, None,
                      "Access to the binary string.")

    @property
    def big_endian(self):
        """Whether the byte order is big endian (bool) **Deprecated**

        Changes how binary string is interpreted when converting to/from a string buffer
        """
        return self._ascending_range

    @big_endian.setter
    def big_endian(self, value):
        if isinstance(value, bool):
            self._ascending_range = value
        else:
            raise TypeError("big_endian is a boolean")

    @property
    def ascending_range(self):
        """Whether the bit order is big endian (bool)

        Changes how the binary string is interpreted when converting between integers
        """
        return self._ascending_range

    @ascending_range.setter
    def ascending_range(self, value):
        if isinstance(value, bool):
            self._ascending_range = value
        else:
            raise TypeError("ascending_range is a boolean")

    @property
    def n_bits(self):
        """Number of bits of the binary value"""
        return self._get_n_bits()

    def _get_n_bits(self):
        """The number of bits of the binary value

        Returns: int or None if unsized
        """
        return self._n_bits

    def hex(self):
        """Get the value as a Python formatted hex string"""
        return self.__hex__()

    def __le__(self, other):
        self.assign(other)

    def __str__(self):
        return self.binstr

    def __repr__(self):
        return self.__str__()

    def __bool__(self):
        return self.__nonzero__()

    def __nonzero__(self):
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
        return any(char == "1" for char in self._str)

    def __eq__(self, other):
        """Two values are equal if they represent the same value

        NOTE: Can be different strings, so long as binary
              representation type is different
        """
        if isinstance(other, BinaryValue):
            other = other.integer
        return self.integer == other

    def __ne__(self, other):
        if isinstance(other, BinaryValue):
            other = other.integer
        return self.integer != other

    def __cmp__(self, other):
        """Comparison against other values"""
        if isinstance(other, BinaryValue):
            other = other.integer
        return self.integer.__cmp__(other)

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
        return pow(self.integer, other, modulo)

    def __ipow__(self, other, modulo=None):
        self.integer = pow(self.integer, other, modulo)
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
        return - self.integer

    def __pos__(self):
        return + self.integer

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
        return self._n_bits or len(self.binstr)

    def _check_index(self, index):
        """Validate the index used when slicing/indexing BinaryValue"""
        length = self.__len__()
        if not isinstance(index, integer_types):
            raise TypeError("BinaryValue only accepts integer indices")
        if index < 0:
            raise IndexError("BinaryValue does not support negative indices")
        if index > length - 1:
            raise IndexError("BinaryValue index {:d} is out of range"
                             "(length {:d})".format(index, length))

    def _handle_slice(self, slice_object):
        """Handles Python slice, formatting it to how BinaryValue can use this

        See __getitem__/__setitem__
        Note: This converts the slice indices from BinaryValue Verilog/VHDL format
              to Python format

        Returns: (slice) Formatted slice
        """
        if slice_object.step is not None:
            raise IndexError("BinaryValue does not support a stepping index")

        max_index = self.__len__() - 1

        if slice_object.start is None:
            slice_object.start = 0 if self.ascending_range else max_index
        if slice_object.stop is None:
            slice_object.stop = max_index if self.ascending_range else 0

        self._check_index(slice_object.start)
        self._check_index(slice_object.stop)

        if self.ascending_range:
            if slice_object.start > slice_object.stop:
                raise IndexError("Big-endian (ascending range) indices "
                                 "must be specified low to high")
            return slice_object
        if slice_object.start < slice_object.stop:
            raise IndexError("Little-endian (descending range) indices "
                             "must be specified high to low")
        # Python lists are always big-endian bit-order, must convert indices
        length = self.__len__()
        high = length - slice_object.stop
        low = length - 1 - slice_object.start
        return slice(low, high)

    def _handle_index(self, key):
        """Handle index passed to __getitem__/__setitem__"""
        if isinstance(key, slice):
            return self._handle_slice(key)
        self._check_index(key)
        if not self.ascending_range:
            # Convert indices to big-endian bit-order
            return self.__len__() - 1 - key
        return key

    def __getitem__(self, key):
        """BinaryValue uses Verilog/VHDL style slices as opposed to Python style

        Step is not supported
        Negative indices are not supported
        Indices are inclusive e.g. [0:3] returns length 4 string
        Indices must be the correct order for bit-order endian-ness of value

        WARNING: When getting a slice, this value is shifted to the 0th index
        """
        key = self._handle_index(key)

        if isinstance(key, slice):
            binstr = self.binstr[key.start:key.stop]
        else:
            binstr = self.binstr[key]
        return BinaryValue(bits=len(binstr),
                           ascendingRange=self.ascending_range,
                           binaryRepresentation=self.binaryRepresentation,
                           value=binstr)

    def __setitem__(self, key, val):
        """BinaryValue uses Verilog/VHDL style slices as opposed to Python style

        Step is not supported
        Negative indices are not supported
        Indices are inclusive e.g. [0:3] returns length 4 string
        Indices must be the correct order for bit-order endian-ness of value
        """
        key = self._handle_index(key)

        if isinstance(key, slice):
            num_slice_bits = abs(key.start - key.stop)
        else:
            num_slice_bits = 1

        if isinstance(val, str):  # We want value as a bit string
            if len(val) != num_slice_bits:
                raise ValueError('String length must be equal to slice '
                                 'length')
        elif isinstance(val, integer_types):
            if val < 0:
                raise ValueError('Integer must be positive')  # Don't know representation of slice
            if val >= pow(2, num_slice_bits):
                raise ValueError('Integer is too large for the specified slice '
                                 'length')
            # If passing an integer, it is a Python int IE little-endian bit-order
            val = "{:0{width}b}".format(val, width=num_slice_bits)
        elif isinstance(val, BinaryValue):
            val = val.binstr
            if len(val) > num_slice_bits:
                raise ValueError("Input BinaryValue is too large for the "
                                 "specified slice length")
        else:
            raise TypeError("BinaryValue slices only accept string, integer, or BinaryValue types")

        if isinstance(key, slice):
            # Endian-ness has already been handled by the index converter
            low = key.start
            high = key.stop
        else:
            # Convert to Python slice
            low = key
            high = key + 1

        self.binstr = self.binstr[:low] + val + self.binstr[high:]

if __name__ == "__main__":
    import doctest
    doctest.testmod()
