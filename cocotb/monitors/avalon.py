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

"""Monitors for Intel Avalon interfaces.

See https://www.intel.com/content/dam/www/programmable/us/en/pdfs/literature/manual/mnl_avalon_spec_1_3.pdf

NB Currently we only support a very small subset of functionality.
"""

from cocotb.utils import hexdump
from cocotb.decorators import coroutine
from cocotb.monitors import BusMonitor
from cocotb.triggers import RisingEdge, ReadOnly
from cocotb.binary import BinaryValue

class AvalonProtocolError(Exception):
    pass


class AvalonST(BusMonitor):
    """Avalon-ST bus.

    Non-packetised so each valid word is a separate transaction.
    """

    _signals = ["valid", "data"]
    _optional_signals = ["ready"]

    _default_config = {"firstSymbolInHighOrderBits": True}

    def __init__(self, *args, **kwargs):
        config = kwargs.pop('config', {})
        BusMonitor.__init__(self, *args, **kwargs)

        self.config = self._default_config.copy()

        for configoption, value in config.items():
            self.config[configoption] = value
            self.log.debug("Setting config option %s to %s", configoption, str(value))

    @coroutine
    def _monitor_recv(self):
        """Watch the pins and reconstruct transactions."""

        # Avoid spurious object creation by recycling
        clkedge = RisingEdge(self.clock)
        rdonly = ReadOnly()

        def valid():
            if hasattr(self.bus, "ready"):
                return self.bus.valid.value and self.bus.ready.value
            return self.bus.valid.value

        # NB could yield on valid here more efficiently?
        while True:
            yield clkedge
            yield rdonly
            if valid():
                vec = self.bus.data.value
                vec.big_endian = self.config["firstSymbolInHighOrderBits"]
                self._recv(vec.buff)


class AvalonSTPkts(BusMonitor):
    """Packetised Avalon-ST bus."""

    _signals = ["valid", "data", "startofpacket", "endofpacket"]
    _optional_signals = ["error", "channel", "ready", "empty"]

    _default_config = {
        "dataBitsPerSymbol"             : 8,
        "firstSymbolInHighOrderBits"    : True,
        "maxChannel"                    : 0,
        "readyLatency"                  : 0,
        "invalidTimeout"                : 0,
    }

    def __init__(self, *args, **kwargs):
        config = kwargs.pop('config', {})
        BusMonitor.__init__(self, *args, **kwargs)

        self.config = self._default_config.copy()

        # Set default config maxChannel to max value on channel bus
        if hasattr(self.bus, 'channel'):
            self.config['maxChannel'] = (2 ** len(self.bus.channel)) -1

        for configoption, value in config.items():
            self.config[configoption] = value
            self.log.debug("Setting config option %s to %s",
                           configoption, str(value))

        num_data_symbols = (len(self.bus.data) /
                            self.config["dataBitsPerSymbol"])
        if (num_data_symbols > 1 and not hasattr(self.bus, 'empty')):
            raise AttributeError(
                "%s has %i data symbols, but contains no object named empty" %
                (self.name, num_data_symbols))

        self.config["useEmpty"] = (num_data_symbols > 1)

        if hasattr(self.bus, 'channel'):
            if "channel" in self._optional_signals:
                self.log.warning("Channel is not fully implemented in this monitor. Recommend use of AvalonSTPktsWithChannel.")

            if len(self.bus.channel) > 128:
                raise AttributeError("AvalonST interface specification defines channel width as 1-128. "
                                     "%d channel width is %d" %
                                     (self.name, len(self.bus.channel)))
            maxChannel = (2 ** len(self.bus.channel)) -1
            if self.config['maxChannel'] > maxChannel:
                raise AttributeError("%s has maxChannel=%d, but can only support a maximum channel of "
                                     "(2**channel_width)-1=%d, channel_width=%d" %
                                     (self.name, self.config['maxChannel'], maxChannel, len(self.bus.channel)))

    @coroutine
    def _monitor_recv(self):
        """Watch the pins and reconstruct transactions."""

        # Avoid spurious object creation by recycling
        clkedge = RisingEdge(self.clock)
        rdonly = ReadOnly()
        pkt = ""
        in_pkt = False
        invalid_cyclecount = 0
        channel = None

        def valid():
            if hasattr(self.bus, 'ready'):
                return self.bus.valid.value and self.bus.ready.value
            return self.bus.valid.value

        while True:
            yield clkedge
            yield rdonly

            if self.in_reset:
                continue

            if valid():
                invalid_cyclecount = 0

                if self.bus.startofpacket.value:
                    if pkt:
                        raise AvalonProtocolError("Duplicate start-of-packet received on %s" %
                                                  str(self.bus.startofpacket))
                    pkt = ""
                    in_pkt = True

                if not in_pkt:
                    raise AvalonProtocolError("Data transfer outside of "
                                              "packet")

                # Handle empty and X's in empty / data
                vec = BinaryValue()
                if not self.bus.endofpacket.value:
                    vec = self.bus.data.value
                else:
                    value = self.bus.data.value.get_binstr()
                    if self.config["useEmpty"] and self.bus.empty.value.integer:
                        empty = self.bus.empty.value.integer * self.config["dataBitsPerSymbol"]
                        if self.config["firstSymbolInHighOrderBits"]:
                            value = value[:-empty]
                        else:
                            value = value[empty:]
                    vec.assign(value)
                    if not vec.is_resolvable:
                        raise AvalonProtocolError("After empty masking value is still bad?  "
                                                  "Had empty {:d}, got value {:s}".format(empty,
                                                                                          self.bus.data.value.get_binstr()))

                vec.big_endian = self.config['firstSymbolInHighOrderBits']
                pkt += vec.buff

                if hasattr(self.bus, 'channel'):
                    if channel is None:
                        channel = self.bus.channel.value.integer
                        if channel > self.config["maxChannel"]:
                            raise AvalonProtocolError("Channel value (%d) is greater than maxChannel (%d)" %
                                                      (channel, self.config["maxChannel"]))
                    elif self.bus.channel.value.integer != channel:
                        raise AvalonProtocolError("Channel value changed during packet")

                if self.bus.endofpacket.value:
                    self.log.info("Received a packet of %d bytes", len(pkt))
                    self.log.debug(hexdump(str((pkt))))
                    self.channel = channel
                    self._recv(pkt)
                    pkt = ""
                    in_pkt = False
                    channel = None
            else:
                if in_pkt:
                    invalid_cyclecount += 1
                    if self.config["invalidTimeout"]:
                        if invalid_cyclecount >= self.config["invalidTimeout"]:
                            raise AvalonProtocolError(
                                "In-Packet Timeout. Didn't receive any valid data for %d cycles!" %
                                invalid_cyclecount)

class AvalonSTPktsWithChannel(AvalonSTPkts):
    """Packetised AvalonST bus using channel."""

    _signals = ["valid", "data", "startofpacket", "endofpacket", "channel"]
    _optional_signals = ["error", "ready", "empty"]

    def __init__(self, *args, **kwargs):
        AvalonSTPkts.__init__(self, *args, **kwargs)

    def _recv(self, pkt):
        """Force use of channel in recv function.

        Args:
            pkt: (string) Monitored data.
        """
        AvalonSTPkts._recv(self, {"data": pkt, "channel": self.channel})
