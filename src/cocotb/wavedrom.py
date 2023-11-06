# Copyright cocotb contributors
# Copyright (c) 2014 Potential Ventures Ltd
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import json
from collections import OrderedDict, defaultdict
from collections.abc import Mapping

import cocotb
from cocotb.handle import SimHandleBase
from cocotb.triggers import ReadOnly, RisingEdge

try:
    from cocotb_bus.bus import Bus
except ImportError:
    Bus = None


class Wavedrom:
    """Base class for a WaveDrom compatible tracer."""

    def __init__(self, obj, name=""):
        self._hdls = OrderedDict()
        self._name = name
        if isinstance(obj, Mapping):
            self._hdls.update(obj)
        elif isinstance(obj, SimHandleBase):
            name = obj._name.split(".")[-1]
            self._hdls[name] = obj
            self._name = name
        elif Bus is not None and isinstance(obj, Bus):
            self._hdls.update(obj._signals)
            self._name = obj._name
        else:
            raise TypeError(
                "Cannot use {} with {} objects".format(
                    type(self).__qualname__, type(obj).__name__
                )
            ) from None
        self.clear()

    def sample(self):
        """Record a sample of the signal value at this point in time."""

        def _lastval(samples):
            for x in range(len(samples) - 1, -1, -1):
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
                if (
                    len(self._data[name])
                    and self._data[name][-1] == int(val)
                    and self._samples[name][-1] in "=."
                ):
                    char = "."
                else:
                    char = "="
                    self._data[name].append(int(val))

            # Detect if this is unchanged
            if len(valstr) == 1 and char == _lastval(self._samples[name]):
                char = "."
            self._samples[name].append(char)

    def clear(self):
        """Delete all sampled data."""
        self._samples = defaultdict(list)
        self._data = defaultdict(list)

    def gap(self):
        for name, hdl in self._hdls.items():
            self._samples[name].append("|")

    def get(self, add_clock=True):
        """Return the samples as a list suitable for use with WaveDrom."""
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
            siglist.insert(0, {"name": "clk", "wave": "p" + "." * (tracelen - 1)})

        return siglist


class trace:
    """Context manager to enable tracing of signals.

    Arguments are an arbitrary number of signals or buses to trace.
    We also require a clock to sample on, passed in as a keyword argument.

    Usage::

        with trace(sig1, sig2, a_bus, clk=clk) as waves:
            # Stuff happens, we trace it

            # Dump to JSON format compatible with WaveDrom
            j = waves.dumpj()
    """

    def __init__(self, *args, clk=None):
        self._clock = clk
        self._signals = []
        for arg in args:
            self._signals.append(Wavedrom(arg))
        self._coro = None
        self._clocks = 0
        self._enabled = False

        if self._clock is None:
            raise ValueError("Trace requires a clock to sample")

    async def _monitor(self):
        self._clocks = 0
        while True:
            await RisingEdge(self._clock)
            await ReadOnly()
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
        self._coro = cocotb.start_soon(self._monitor())
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
            {"name": "clock", "wave": "p" + "." * (self._clocks - 1)}
        )
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
