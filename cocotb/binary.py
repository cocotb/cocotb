#!/usr/bin/env python

''' Copyright (c) 2013 Potential Ventures Ltd
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd nor the
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

def resolve(string):
    for char in "xXzZ":
        string = string.replace(char, "0")
    return string


class BinaryValue(object):
    """Represenatation of values in binary format.

    The underlying value can be set or accessed using three aliasing attributes,

        - BinaryValue.value is an integer
        - BinaryValue.binstr is a string of "01xXzZ"
        - BinaryValue.buff is a binary buffer of bytes

    For example:

    >>> vec = BinaryValue()
    >>> vec.value = 42
    >>> print vec.binstr
    101010
    >>> print repr(vec.buff)
    '*'

    """
    _permitted_chars = "01xXzZ"


    def __init__(self, value=None, bits=None):
        self._str = ""
        self._bits = bits

        if value is not None:
            self.assign(value)

    def assign(self, value):
        """Decides how best to assign the value to the vector

        We possibly try to be a bit too clever here by first of
        all trying to assign the raw string as a binstring, however
        if the string contains any characters that aren't 0, 1, X or Z
        then we interpret the string as a binary buffer...
        """
        if isinstance(value, int):
            self.value = value
        elif isinstance(value, str):
            try:
                self.binstr = value
            except ValueError:
                self.buff = value

    def get_value(self):
        """value is an integer representaion of the underlying vector"""
        return int(resolve(self._str), 2)

    def set_value(self, integer):
        self._str = "{:b}".format(integer)
        self._adjust()

    value = property(get_value, set_value, None, "Integer access to the value")

    def get_buff(self):
        """Attribute self.buff represents the value as a binary string buffer
            e.g. vector "0000000100011111".buff == "\x01\x1F"
            TODO: Doctest this!
        """
        bits = self._str
        if len(bits) % 8: bits = "0" * (8 - len(bits) % 8) + bits
        bits = resolve(bits)
        buff = ""
        while bits:
            byte = bits[:8]
            bits = bits[8:]
            val = int(byte, 2)
            buff += chr(val)
        return buff

    def set_buff(self, buff):
        self._str = ""
        for char in buff:
            self._str = "{:08b}".format(ord(char)) + self._str
        self._adjust()

    buff = property(get_buff, set_buff, None, "Access to the value as a buffer")

    def get_binstr(self):
        """Attribute binstr is the binary representation stored as a string of 1s and 0s"""
        return self._str

    def set_binstr(self, string):
        for char in string:
            if char not in BinaryValue._permitted_chars:
                raise ValueError("Attempting to assign character %s to a %s" % (char, self.__class__.__name__))
        self._str = string
        self._adjust()

    binstr = property(get_binstr, set_binstr, None, "Access to the binary string")

    def _adjust(self):
        """Pad/truncate the bit string to the correct length"""
        if self._bits is None:
            return
        l = len(self._str)
        if l < self._bits:
            self._str = "0" * (l-self._bits) + self._str
        elif l > self._bits:
            print "WARNING truncating value to match requested number of bits (%d)" % l
            self._str = self._str[l - self._bits:]

    def __le__(self, other):
        self.assign(other)

    def __str__(self):
        return "%d" % (self.value)

    def __nonzero__(self):
        """Provide boolean testing of a binstr.

        >>> val = BinaryValue("0000")
        >>> if val: print "True"
        ... else:   print "False"
        False
        >>> val.value = 42
        >>> if val: print "True"
        ... else:   print "False"
        True

        """
        for char in self._str:
            if char == "1": return True
        return False

    def __cmp__(self, other):
        """Comparison against other values"""
        if isinstance(other, BinaryValue):
            other = other.value
        return self.value.__cmp__(other)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
