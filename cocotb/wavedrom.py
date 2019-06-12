'''
Copyright (c) 2014 Potential Ventures Ltd
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd, nor the
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

import json
from collections import OrderedDict, defaultdict

import cocotb
from cocotb.bus import Bus
from cocotb.triggers import RisingEdge, ReadOnly
from cocotb.utils import reject_remaining_kwargs


class Wavedrom(object):
    """
    Base class for a wavedrom compatible tracer
    """
    def __init__(self, obj):

        self._hdls = OrderedDict()
        if isinstance(obj, Bus):
            for name in sorted(obj._signals.keys()):
                self._hdls[name] = obj._signals[name]
            self._name = obj._name
        else:
            self._hdls[obj._name.split(".")[-1]] = obj

        self.clear()

    def sample(self):
        """
        Record a sample of the signal value at this point in time
        """

        def _lastval(samples):
            for x in range(len(samples)-1, -1, -1):
                if samples[x] not in "=.|":
                    return samples[x]
            return None

        for name, hdl in self._hdls.items():
            val = hdl.value
            valstr = val.binstr.lower()

            # Decide what character to use to represent this signal
            if len(valstr) == 1:
                char = valstr
            elif "x" in valstr:
                char = "x"
            elif "u" in valstr:
                char = "u"
            elif "z" in valstr:
                char = "z"
            else:
                if (len(self._data[name]) and
                        self._data[name][-1] == int(val) and
                        self._samples[name][-1] in "=."):
                    char = "."
                else:
                    char = "="
                    self._data[name].append(int(val))

            # Detect if this is unchanged
            if len(valstr) == 1 and char == _lastval(self._samples[name]):
                char = "."
            self._samples[name].append(char)

    def clear(self):
        """
        Delete all sampled data
        """
        self._samples = defaultdict(list)
        self._data = defaultdict(list)

    def gap(self):
        for name, hdl in self._hdls.items():
            self._samples[name].append("|")

    def get(self, add_clock=True):
        """
        Return the samples as a list suitable for use with WaveDrom
        """
        siglist = []
        traces = []
        for name in self._hdls.keys():
            samples = self._samples[name]
            traces.append({"name": name, "wave": "".join(samples)})
            if name in self._data:
                traces[-1]["data"] = " ".join([repr(s) for s in self._data[name]])

        if len(traces) > 1:
            traces.insert(0, self._name)
            siglist.append(traces)
        else:
            siglist.append(traces[0])

        if add_clock:
            tracelen = len(traces[-1]["wave"])
            siglist.insert(0, {"name": "clk", "wave": "p" + "."*(tracelen-1)})

        return siglist


class trace(object):
    """
    Context manager to enable tracing of signals

    Arguments are an arbitrary number of signals or busses to trace.

    We also require a clock to sample on, passed in as a keyword argument

    Usage:

        with trace(sig1, sig2, a_bus, clk=clk) as waves:
            # Stuff happens, we trace it

            # Dump to JSON format compatible with wavedrom
            j = waves.dumpj()
    """

    def __init__(self, *args, **kwargs):
        # emulate keyword-only arguments in python 2
        self._clock = kwargs.pop("clk", None)
        reject_remaining_kwargs('__init__', kwargs)

        self._signals = []
        for arg in args:
            self._signals.append(Wavedrom(arg))
        self._coro = None
        self._clocks = 0
        self._enabled = False

        if self._clock is None:
            raise ValueError("Trace requires a clock to sample")

    @cocotb.coroutine
    def _monitor(self):
        self._clocks = 0
        while True:
            yield RisingEdge(self._clock)
            yield ReadOnly()
            if not self._enabled:
                continue
            self._clocks += 1
            for sig in self._signals:
                sig.sample()

    def insert_gap(self):
        self._clocks += 1
        for sig in self._signals:
            sig.gap()

    def disable(self):
        self._enabled = False

    def enable(self):
        self._enabled = True

    def __enter__(self):
        for sig in self._signals:
            sig.clear()
        self.enable()
        self._coro = cocotb.fork(self._monitor())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._coro.kill()
        for sig in self._signals:
            sig.clear()
        self.disable()
        return None

    def write(self, filename, **kwargs):
        with open(filename, "w") as f:
            f.write(self.dumpj(**kwargs))

    def dumpj(self, header="", footer="", config=""):
        trace = {"signal": []}
        trace["signal"].append(
            {"name": "clock", "wave": "p" + "."*(self._clocks-1)})
        for sig in self._signals:
            trace["signal"].extend(sig.get(add_clock=False))
        if header:
            if isinstance(header, dict):
                trace["head"] = header
            else:
                trace["head"] = {"text": header}
        if footer:
            if isinstance(footer, dict):
                trace["foot"] = footer
            else:
                trace["foot"] = {"text": footer}
        if config:
            trace["config"] = config
        return json.dumps(trace, indent=4, sort_keys=False)
