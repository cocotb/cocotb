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


"""
    Collection of generators for creating byte streams.

    Note that on Python 3, individual bytes are represented with integers.
"""
import random
import itertools
from cocotb.decorators import public
from typing import Iterator


@public
def get_bytes(nbytes: int, generator: Iterator[int]) -> bytes:
    """
    Get *nbytes* bytes from *generator*

    .. versionchanged:: 1.4.0
        This now returns :class:`bytes`, not :class:`str`.

    .. deprecated:: 1.4.1
    """
    return bytes(next(generator) for i in range(nbytes))


@public
def random_data() -> Iterator[int]:
    r"""
    Random bytes

    .. versionchanged:: 1.4.0
        This now returns integers, not single-character :class:`str`\ s.

    .. deprecated:: 1.4.1
    """
    while True:
        yield random.randrange(256)


@public
def incrementing_data(increment=1) -> Iterator[int]:
    r"""
    Incrementing bytes

    .. versionchanged:: 1.4.0
        This now returns integers, not single-character :class:`str`\ s.

    .. deprecated:: 1.4.1
    """
    val = 0
    while True:
        yield val
        val += increment
        val = val & 0xFF


@public
def repeating_bytes(pattern: bytes = b"\x00") -> Iterator[int]:
    """
    Repeat a pattern of bytes

    .. deprecated:: 1.4.1
    """
    return itertools.cycle(pattern)
