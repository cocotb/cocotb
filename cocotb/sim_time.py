''' Copyright (c) 2016 Luke Darnell
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Broadcom nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL BROADCOM BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. '''


import simulator

sim_precision = simulator.get_precision()

def time_in_s():
    """
    Return the current simulation time in seconds.
    """
    timeh, timel = simulator.get_sim_time()
    time_s = (timeh << 32 | timel) * (10.0**sim_precision)
    return time_s

def s(time):
    """
    Return the closest possible representation of the incoming 
    argument (speficied in seconds) in simulator time ticks.
    This is suitable for getting a predictable delay in cocotb. 
    e.g
    yield Timer(s(5))
    """
    counts = (time) / 1e1**sim_precision
    return int(round(counts))

def ms(time):
    """
    Return the closest possible representation of the incoming 
    argument (speficied in milliseconds) in simulator time ticks.
    This is suitable for getting a predictable delay in cocotb. 
    e.g
    yield Timer(ms(5))
    """
    counts = (time*1e-3) / 1e1**sim_precision
    return int(round(counts))

def us(time):
    """
    Return the closest possible representation of the incoming 
    argument (speficied in microseconds) in simulator time ticks.
    This is suitable for getting a predictable delay in cocotb. 
    e.g
    yield Timer(us(5))
    """
    counts = (time*1e-6) / 1e1**sim_precision
    return int(round(counts))

def ns(time):
    """
    Return the closest possible representation of the incoming 
    argument (speficied in nanoseconds) in simulator time ticks.
    This is suitable for getting a predictable delay in cocotb. 
    e.g
    yield Timer(ns(5))
    """
    counts = (time*1e-9) / 1e1**sim_precision
    return int(round(counts))

def ps(time):
    """
    Return the closest possible representation of the incoming 
    argument (speficied in picoseconds) in simulator time ticks.
    This is suitable for getting a predictable delay in cocotb. 
    e.g
    yield Timer(ps(5))
    """
    counts = (time*1e-12) / 1e1**sim_precision
    return int(round(counts))

def fs(time):
    """
    Return the closest possible representation of the incoming 
    argument (speficied in picoseconds) in simulator time ticks.
    This is suitable for getting a predictable delay in cocotb. 
    e.g
    yield Timer(fs(5))
    """
    counts = (time*1e-15) / 1e1**sim_precision
    return int(round(counts))
