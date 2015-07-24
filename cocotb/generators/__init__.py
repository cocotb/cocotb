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

"""
    Set of general generic generators
"""
import math
import random
from cocotb.decorators import public


@public
def repeat(obj, nrepeat=None):
    """Generator to repeatedly yield the same object

    Args:
        obj (any): The object to yield

    Kwargs:
        nrepeat (int): The number of times to repeatedly yield obj
    """
    if nrepeat is None:
        while True:
            yield obj
    else:
        for i in range(nrepeat):
            yield obj


@public
def combine(generators):
    """
    Generator for serially combining multiple generators together

    Args:
        generators (iterable): Generators to combine together
    """
    for gen in generators:
        for item in gen:
            yield item


@public
def gaussian(mean, sigma):
    """
    Generate a guasian distribution indefinitely

    Args:
        mean (int/float): mean value

        signma (int/float): Standard deviation
    """
    while True:
        yield random.gauss(mean, sigma)


@public
def sine_wave(amplitude, w, offset=0):
    """
    Generates a sine wave that repeats forever

    Args:
        amplitude (int/float):  peak deviation of the function from zero

        w (int/float): is the rate of change of the function argument

    Yields:
        floats that form a sine wave
    """
    twoPiF_DIV_sampleRate = math.pi * 2
    while True:
        for idx in (i / float(w) for i in range(int(w))):
            yield amplitude*math.sin(twoPiF_DIV_sampleRate * idx) + offset


def get_generators(module):
    """Return an iterator which yields  all the generators in a module

    Args:
        module (python module): The module to get the generators from
    """
    return (getattr(module, gen) for gen in module.__all__)
