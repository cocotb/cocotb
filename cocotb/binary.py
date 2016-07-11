#!/usr/bin/env python

''' Copyright (c) 2013 Potential Ventures Ltd
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

from __future__ import print_function
from math import log, ceil
from cocotb.utils import get_python_integer_types


def resolve(string):
    for char in BinaryValue._resolve_to_0:
        string = string.replace(char, "0")
    for char in BinaryValue._resolve_to_1:
        string = string.replace(char, "1")
    if any(char in string for char in BinaryValue._resolve_to_error):
        raise ValueError("Unable to resolve to binary >%s<" % string)
    return string


class BinaryRepresentation():
    UNSIGNED         = 0  # noqa
    SIGNED_MAGNITUDE = 1  # noqa
    TWOS_COMPLEMENT  = 2  # noqa


class BinaryValue(object):
    """Represenatation of values in binary format.

    The underlying value can be set or accessed using three aliasing attributes

        - BinaryValue.integer is an integer
        - BinaryValue.signed_integer is a signed integer
        - BinaryValue.binstr is a string of "01xXzZ"
        - BinaryValue.buff is a binary buffer of bytes

        - BinaryValue.value is an integer *** deprecated ***

    For example:

    >>> vec = BinaryValue()
    >>> vec.integer = 42
    >>> print vec.binstr
    101010
    >>> print repr(vec.buff)
    '*'

    """
    _resolve_to_0     = "-lL"  # noqa
    _resolve_to_1     = "hH"  # noqa
    _resolve_to_error = "xXzZuUwW"  # Resolve to a ValueError() since these usually mean something is wrong
    _permitted_chars  = _resolve_to_0 +_resolve_to_1 + _resolve_to_error + "01"  # noqa

    def __init__(self, value=None, bits=None, bigEndian=True,
                 binaryRepresentation=BinaryRepresentation.UNSIGNED):
        """
        Kwagrs:
            Value (string or int or long): value to assign to the bus

            bits (int): Number of bits to use for the underlying binary
                        representation

            bigEndian (bool): Interpret the binary as big-endian when
                                converting to/from a string buffer.
        """
        self._str = ""
        self._bits = bits
        self.big_endian = bigEndian
        self.binaryRepresentation = binaryRepresentation
        self._convert_to = {
                            BinaryRepresentation.UNSIGNED         : self._convert_to_unsigned   ,
                            BinaryRepresentation.SIGNED_MAGNITUDE : self._convert_to_signed_mag ,
                            BinaryRepresentation.TWOS_COMPLEMENT  : self._convert_to_twos_comp  ,
                            }

        self._convert_from = {
                            BinaryRepresentation.UNSIGNED         : self._convert_from_unsigned   ,
                            BinaryRepresentation.SIGNED_MAGNITUDE : self._convert_from_signed_mag ,
                            BinaryRepresentation.TWOS_COMPLEMENT  : self._convert_from_twos_comp  ,
                            }

        if value is not None:
            self.assign(value)

    def assign(self, value):
        """Decides how best to assign the value to the vector

        We possibly try to be a bit too clever here by first of
        all trying to assign the raw string as a binstring, however
        if the string contains any characters that aren't 0, 1, X or Z
        then we interpret the string as a binary buffer...
        """
        if isinstance(value, get_python_integer_types()):
            self.value = value
        elif isinstance(value, str):
            try:
                self.binstr = value
            except ValueError:
                self.buff = value

    def _convert_to_unsigned(self, x):
        x = bin(x)
        if x[0] == '-':
            raise ValueError('Attempt to assigned negative number to unsigned '
                             'BinaryValue')
        return self._adjust_unsigned(x[2:])

    def _convert_to_signed_mag(self, x):
        x = bin(x)
        if x[0] == '-':
            binstr = self._adjust_signed_mag('1' + x[3:])
        else:
            binstr = self._adjust_signed_mag('0' + x[2:])
        if self.big_endian:
            binstr = binstr[::-1]
        return binstr

    def _convert_to_twos_comp(self, x):
        if x < 0:
            ceil_log2 = int(ceil(log(abs(x), 2)))
            binstr = bin(2 ** (ceil_log2 + 1) + x)[2:]
            binstr = self._adjust_twos_comp(binstr)
        else:
            binstr = self._adjust_twos_comp('0' + bin(x)[2:])
        if self.big_endian:
            binstr = binstr[::-1]
        return binstr

    def _convert_from_unsigned(self, x):
        return int(resolve(x), 2)

    def _convert_from_signed_mag(self, x):
        rv = int(resolve(self._str[1:]), 2)
        if self._str[0] == '1':
            rv = rv * -1
        return rv

    def _convert_from_twos_comp(self, x):
        if x[0] == '1':
            binstr = x[1:]
            binstr = self._invert(binstr)
            rv = int(binstr, 2) + 1
            if x[0] == '1':
                rv = rv * -1
        else:
            rv = int(resolve(x), 2)
        return rv

    def _invert(self, x):
        inverted = ''
        for bit in x:
            if bit == '0':
                inverted = inverted + '1'
            elif bit == '1':
                inverted = inverted + '0'
            else:
                inverted = inverted + bit
        return inverted

    def _adjust_unsigned(self, x):
        if self._bits is None:
            return x
        l = len(x)
        if l <= self._bits:
            if self.big_endian:
                rv = x + '0' * (self._bits - l)
            else:
                rv = '0' * (self._bits - l) + x
        elif l > self._bits:
            print("WARNING truncating value to match requested number of bits "
                  "(%d -> %d)" % (l, self._bits))
            if self.big_endian:
                rv = x[l - self._bits:]
            else:
                rv = x[:l - self._bits]
        return rv

    def _adjust_signed_mag(self, x):
        """Pad/truncate the bit string to the correct length"""
        if self._bits is None:
            return x
        l = len(x)
        if l <= self._bits:
            if self.big_endian:
                rv = x[:-1] + '0' * (self._bits - 1 - l)
                rv = rv + x[-1]
            else:
                rv = '0' * (self._bits - 1 - l) + x[1:]
                rv = x[0] + rv
        elif l > self._bits:
            print("WARNING truncating value to match requested number of bits "
                  "(%d -> %d)" % (l, self._bits))
            if self.big_endian:
                rv = x[l - self._bits:]
            else:
                rv = x[:-(l - self._bits)]
        else:
            rv = x
        return rv

    def _adjust_twos_comp(self, x):
        if self._bits is None:
            return x
        l = len(x)
        if l <= self._bits:
            if self.big_endian:
                rv = x + x[-1] * (self._bits - l)
            else:
                rv = x[0] * (self._bits - l) + x
        elif l > self._bits:
            print("WARNING truncating value to match requested number of bits "
                  "(%d -> %d)" % (l, self._bits))
            if self.big_endian:
                rv = x[l - self._bits:]
            else:
                rv = x[:-(l - self._bits)]
        else:
            rv = x
        return rv

    def get_value(self):
        """value is an integer representaion of the underlying vector"""
        return self._convert_from[self.binaryRepresentation](self._str)

    def get_value_signed(self):
        """value is an signed integer representaion of the underlying vector"""
        ival = int(resolve(self._str), 2)
        bits = len(self._str)
        signbit = (1 << (bits - 1))
        if (ival & signbit) == 0:
            return ival
        else:
            return -1 * (1 + (int(~ival) & (signbit - 1)))

    def set_value(self, integer):
        self._str = self._convert_to[self.binaryRepresentation](integer)

    value = property(get_value, set_value, None,
                     "Integer access to the value *** deprecated ***")
    integer = property(get_value, set_value, None,
                       "Integer access to the value")
    signed_integer = property(get_value_signed, set_value, None,
                              "Signed integer access to the value")

    def get_buff(self):
        """Attribute self.buff represents the value as a binary string buffer

        >>> "0100000100101111".buff == "\x41\x2F"
        True

        """
        bits = resolve(self._str)
        if len(bits) % 8:
            bits = "0" * (8 - len(bits) % 8) + bits

        buff = ""
        while bits:
            byte = bits[:8]
            bits = bits[8:]
            val = int(byte, 2)
            if self.big_endian:
                buff += chr(val)
            else:
                buff = chr(val) + buff
        return buff

    def get_hex_buff(self):
        bstr = self.get_buff()
        hstr = '%0*X' % ((len(bstr) + 3) // 4, int(bstr, 2))
        return hstr

    def set_buff(self, buff):
        self._str = ""
        for char in buff:
            if self.big_endian:
                self._str += "{0:08b}".format(ord(char))
            else:
                self._str = "{0:08b}".format(ord(char)) + self._str
        self._adjust()

    def _adjust(self):
        """Pad/truncate the bit string to the correct length"""
        if self._bits is None:
            return
        l = len(self._str)
        if l < self._bits:
            if self.big_endian:
                self._str = self._str + "0" * (self._bits - l)
            else:
                self._str = "0" * (self._bits - l) + self._str
        elif l > self._bits:
            print("WARNING truncating value to match requested number of bits "
                  " (%d)" % l)
            self._str = self._str[l - self._bits:]

    buff = property(get_buff, set_buff, None,
                    "Access to the value as a buffer")

    def get_binstr(self):
        """Attribute binstr is the binary representation stored as a string of
        1s and 0s"""
        return self._str

    def set_binstr(self, string):
        for char in string:
            if char not in BinaryValue._permitted_chars:
                raise ValueError("Attempting to assign character %s to a %s" %
                                 (char, self.__class__.__name__))
        self._str = string
        self._adjust()

    binstr = property(get_binstr, set_binstr, None,
                      "Access to the binary string")

    def hex(self):
        try:
            return hex(self.get_value())
        except:
            return hex(int(self.binstr, 2))

    def __le__(self, other):
        self.assign(other)

    def __str__(self):
        return self.binstr

    def __bool__(self):
        return self.__nonzero__()

    def __nonzero__(self):
        """Provide boolean testing of a binstr.

        >>> val = BinaryValue("0000")
        >>> if val: print "True"
        ... else:   print "False"
        False
        >>> val.integer = 42
        >>> if val: print "True"
        ... else:   print "False"
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

    def __cmp__(self, other):
        """Comparison against other values"""
        if isinstance(other, BinaryValue):
            other = other.value
        return self.value.__cmp__(other)

    def __int__(self):
        return self.integer

    def __long__(self):
        return self.integer

    def __add__(self, other):
        return self.integer + int(other)

    def __iadd__(self, other):
        self.integer = self.integer + int(other)
        return self

    def __sub__(self, other):
        return self.integer - int(other)

    def __isub__(self, other):
        self.integer = self.integer - int(other)
        return self

    def __mul__(self, other):
        return self.integer * int(other)

    def __imul__(self, other):
        self.integer = self.integer * int(other)
        return self

    def __divmod__(self, other):
        return self.integer // int(other)

    def __idivmod__(self, other):
        self.integer = self.integer // int(other)
        return self

    def __mod__(self, other):
        return self.integer % int(other)

    def __imod__(self, other):
        self.integer = self.integer % int(other)
        return self

    def __lshift__(self, other):
        return int(self) << int(other)

    def __ilshift__(self, other):
        """Preserves X values"""
        self.binstr = self.binstr[other:] + self.binstr[:other]
        return self

    def __rshift__(self, other):
        return int(self) >> int(other)

    def __irshift__(self, other):
        """Preserves X values"""
        self.binstr = self.binstr[-other:] + self.binstr[:-other]
        return self

    def __invert__(self):
        """Preserves X values"""
        self.binstr = self._invert(self.binstr)
        return self

    def __len__(self):
        return len(self.binstr)

    def __getitem__(self, key):
        ''' BinaryValue uses verilog/vhdl style slices as opposed to python
        style'''
        if isinstance(key, slice):
            first, second = key.start, key.stop
            if self.big_endian:
                if first < 0 or second < 0:
                    raise IndexError('BinaryValue does not support negative '
                                     'indices')
                if second > self._bits - 1:
                    raise IndexError('High index greater than number of bits.')
                if first > second:
                    raise IndexError('Big Endian indices must be specified '
                                     'low to high')
                _binstr = self.binstr[first:(second + 1)]
            else:
                if first < 0 or second < 0:
                    raise IndexError('BinaryValue does not support negative '
                                     'indices')
                if first > self._bits - 1:
                    raise IndexError('High index greater than number of bits.')
                if second > first:
                    raise IndexError('Litte Endian indices must be specified '
                                     'high to low')
                high = self._bits - second
                low = self._bits - 1 - first
                _binstr = self.binstr[low:high]
        else:
            index = key
            if index > self._bits - 1:
                raise IndexError('Index greater than number of bits.')
            if self.big_endian:
                _binstr = self.binstr[index]
            else:
                _binstr = self.binstr[self._bits-1-index]
        rv = BinaryValue(bits=len(_binstr), bigEndian=self.big_endian,
                         binaryRepresentation=self.binaryRepresentation)
        rv.set_binstr(_binstr)
        return rv

    def __setitem__(self, key, val):
        ''' BinaryValue uses verilog/vhdl style slices as opposed to python
        style'''
        if not isinstance(val, str):
            raise TypeError('BinaryValue slices only accept string values')
        if isinstance(key, slice):
            first, second = key.start, key.stop
            if self.big_endian:
                if first < 0 or second < 0:
                    raise IndexError('BinaryValue does not support negative '
                                     'indices')
                if second > self._bits - 1:
                    raise IndexError('High index greater than number of bits.')
                if first > second:
                    raise IndexError('Big Endian indices must be specified '
                                     'low to high')
                if len(val) > (second + 1 - first):
                    raise ValueError('String length must be equal to slice '
                                     'length')
                slice_1 = self.binstr[:first]
                slice_2 = self.binstr[second + 1:]
                self.binstr = slice_1 + val + slice_2
            else:
                if first < 0 or second < 0:
                    raise IndexError('BinaryValue does not support negative '
                                     'indices')
                if first > self._bits - 1:
                    raise IndexError('High index greater than number of bits.')
                if second > first:
                    raise IndexError('Litte Endian indices must be specified '
                                     'high to low')
                high = self._bits - second
                low = self._bits - 1 - first
                if len(val) > (high - low):
                    raise ValueError('String length must be equal to slice '
                                     'length')
                slice_1 = self.binstr[:low]
                slice_2 = self.binstr[high:]
                self.binstr = slice_1 + val + slice_2
        else:
            index = key
            if index > self._bits - 1:
                raise IndexError('Index greater than number of bits.')
            if self.big_endian:
                self.binstr = self.binstr[:index] + val + self.binstr[index + 1:]
            else:
                self.binstr = self.binstr[0:self._bits-index-1] + val + self.binstr[self._bits-index:self._bits]

if __name__ == "__main__":
    import doctest
    doctest.testmod()
