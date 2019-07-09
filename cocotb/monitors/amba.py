""" Copyright 2019 by Ben Coughlan <ben@liquidinstruments.com>

Licensed under Revised BSD License
All rights reserved. See LICENSE.
"""

import cocotb
from cocotb.monitors import BusMonitor
from cocotb.triggers import RisingEdge

class AXI4(BusMonitor):
    """AXI4 Bus

    Just monitors for transaction on each channel, doesn't consider
    transactions across multiple channels.
    """
    _signals = ["awvalid", "awready", "awaddr",
                "wvalid", "wready", "wdata",
                "bvalid", "bready", "bid",
                "arvalid", "arready", "araddr",
                "rvalid", "rready", "rdata"]
    _optional_signals = []

    @cocotb.coroutine
    def _monitor_recv(self):
        while True:
            yield RisingEdge(self.clock)

            if self.bus.awvalid.value and self.bus.awready.value:
                self._recv(('awaddr', int(self.bus.awaddr)))

            if self.bus.wvalid.value and self.bus.wready.value:
                self._recv(('wdata', int(self.bus.wdata)))

            if self.bus.bvalid.value and self.bus.bready.value:
                self._recv(('bid', self.bus.bid.value))

            if self.bus.arvalid.value and self.bus.arready.value:
                self._recv(('araddr', int(self.bus.araddr)))

            if self.bus.rvalid.value and self.bus.rready.value:
                self._recv(('rdata', int(self.bus.rdata)))
