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
Monitors for Altera Avalon interfaces.

See http://www.altera.co.uk/literature/manual/mnl_avalon_spec.pdf

NB Currently we only support a very small subset of functionality
"""
from cocotb.utils import hexdump
from cocotb.decorators import coroutine
from cocotb.monitors import BusMonitor
from cocotb.triggers import RisingEdge, ReadOnly


class AvalonProtocolError(Exception):
    pass


class AvalonST(BusMonitor):
    """
    AvalonST bus.

    Non-packetised so each valid word is a separate transaction
    """
    _signals = ["valid", "data"]

    @coroutine
    def _monitor_recv(self):
        """Watch the pins and reconstruct transactions"""

        # Avoid spurious object creation by recycling
        clkedge = RisingEdge(self.clock)
        rdonly = ReadOnly()

        # NB could yield on valid here more efficiently?
        while True:
            yield clkedge
            yield rdonly
            if self.bus.valid.value:
                vec = self.bus.data.value
                self._recv(vec.buff)


class AvalonSTPkts(BusMonitor):
    """
    Packetised AvalonST bus
    """
    _signals = ["valid", "data", "startofpacket", "endofpacket", "empty"]
    _optional_signals = ["error", "channel", "ready"]

    _default_config = {
        "dataBitsPerSymbol"             : 8,
        "firstSymbolInHighOrderBits"    : True,
        "maxChannel"                    : 0,
        "readyLatency"                  : 0
    }

    def __init__(self, *args, **kwargs):
        config = kwargs.pop('config', {})
        BusMonitor.__init__(self, *args, **kwargs)

        self.config = AvalonSTPkts._default_config.copy()

        for configoption, value in config.items():
            self.config[configoption] = value
            self.log.debug("Setting config option %s to %s" %
                           (configoption, str(value)))

    @coroutine
    def _monitor_recv(self):
        """Watch the pins and reconstruct transactions"""

        # Avoid spurious object creation by recycling
        clkedge = RisingEdge(self.clock)
        rdonly = ReadOnly()
        pkt = ""
        in_pkt = False

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
                if self.bus.startofpacket.value:
                    if pkt:
                        raise AvalonProtocolError(
                            "Duplicate start-of-packet received on %s" % (
                                str(self.bus.startofpacket)))
                    pkt = ""
                    in_pkt = True

                if not in_pkt:
                    raise AvalonProtocolError("Data transfer outside of "
                                              "packet")

                vec = self.bus.data.value
                vec.big_endian = self.config['firstSymbolInHighOrderBits']
                pkt += vec.buff

                if self.bus.endofpacket.value:
                    # Truncate the empty bits
                    if self.bus.empty.value.integer:
                        pkt = pkt[:-self.bus.empty.value.integer]
                    self.log.info("Received a packet of %d bytes" % len(pkt))
                    self.log.debug(hexdump(str((pkt))))
                    self._recv(pkt)
                    pkt = ""
                    in_pkt = False
