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
    Collection of generators for creating bit signals.

    Typically we use a single bit to control backpressure or insert IDLE
    cycles onto a bus.

    These yield a tuple which is intended to be interpreted as a number of
    cycles (ON,OFF)
"""
import sys

from cocotb.decorators import public
from cocotb.generators import *

if sys.version_info.major < 3:
    # zip is not lazy on python 2, so use itertools
    import itertools
    izip = itertools.izip
else:
    izip = zip


def bit_toggler(gen_on, gen_off):
    """Combines two generators to provide cycles_on, cycles_off tuples

    Args:
        gen_on (generator): generator that yields number of cycles on

        gen_off (generator): generator that yields number of cycles off
    """
    for n_on, n_off in izip(gen_on, gen_off):
        yield int(abs(n_on)), int(abs(n_off))


@public
def intermittent_single_cycles(mean=10, sigma=None):
    """Generator to intermittently insert a single cycle pulse

    Kwargs:
        mean (int):     Average number of cycles in between single cycle gaps

        sigma (int):    Standard deviation of gaps.  mean/4 if sigma is None
    """
    if sigma is None:
        sigma = mean / 4.0

    return bit_toggler(gaussian(mean, sigma), repeat(1))


@public
def random_50_percent(mean=10, sigma=None):
    """50% duty cycle with random width
    Kwargs:
        mean (int):     Average number of cycles on/off

        sigma (int):    Standard deviation of gaps.  mean/4 if sigma is None
    """
    if sigma is None:
        sigma = mean / 4.0
    for duration in gaussian(mean, sigma):
        yield int(abs(duration)), int(abs(duration))


@public
def wave(on_ampl=30, on_freq=200, off_ampl=10, off_freq=100):
    """
    Drive a repeating sine_wave pattern

    TODO:
        Adjust args so we just specify a repeat duration and overall throughput
    """
    return bit_toggler(sine_wave(on_ampl, on_freq),
                       sine_wave(off_ampl, off_freq))
