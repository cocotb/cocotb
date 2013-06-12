#! /usr/bin/env python
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

from scapy.all import *

#define all the fields as extensions of the current base classes that need it

STRUCT_FMT = {
    8  : 'B',   # unsigned char
    16 : 'H',   # unsigned short
    32 : 'I',   # unsigned int
}

def int_to_words(int_val, num_words=4, word_size=32):
    max_int = 2 ** (word_size*num_words) - 1
    max_word_size = 2 ** word_size - 1

    if not 0 <= int_val <= max_int:
        raise IndexError('integer %r is out of bounds!' % hex(int_val))

    words = []
    for _ in range(num_words):
        word = int_val & max_word_size
        words.append(int(word))
        int_val >>= word_size
    words.reverse()

    return words

def int_to_packed(int_val, width=128, word_size=32):
    num_words = width / word_size
    words = int_to_words(int_val, num_words, word_size)

    try:
        fmt = '>%d%s' % (num_words, STRUCT_FMT[word_size])
        #DEBUG: print 'format:', fmt
    except KeyError:
        raise ValueError('unsupported word size: %d!' % word_size)

    return struct.pack(fmt, *words)

def packed_to_int(packed_int, width=128, word_size=32):
    num_words = width / word_size

    try:
        fmt = '>%d%s' % (num_words, STRUCT_FMT[word_size])
        #DEBUG: print 'format:', fmt
    except KeyError:
        raise ValueError('unsupported word size: %d!' % word_size)

    words = list(struct.unpack(fmt, packed_int))
    words.reverse()

    int_val = 0
    for i, num in enumerate(words):
        word = num
        word = word << word_size * i
        int_val = int_val | word

    return int_val

class LongDecimalField(StrFixedLenField):
    def __init__(self, name, default, length):
        StrFixedLenField.__init__(self, name, default, length, None)
        self.length = length

    def addfield(self, pkt, s, val):
        return s + int_to_packed(val, self.length * 8, 8)

    def extract_padding(self, s):
        return '', s
