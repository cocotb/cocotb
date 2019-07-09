# Copyright (c) 2014 Potential Ventures Ltd
# Copyright 2019 by Ben Coughlan <ben@liquidinstruments.com>
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

"""Drivers for Advanced Microcontroller Bus Architecture."""

import cocotb
from cocotb.triggers import RisingEdge, ReadOnly, Lock
from cocotb.drivers import BusDriver
from cocotb.result import ReturnValue
from cocotb.utils import int_to_bytes, int_from_bytes


class AXIProtocolError(Exception):
    pass


class AXI4LiteMaster(BusDriver):
    """AXI4-Lite Master.

    TODO: Kill all pending transactions if reset is asserted.
    """

    _signals = ["AWVALID", "AWADDR", "AWREADY",        # Write address channel
                "WVALID", "WREADY", "WDATA", "WSTRB",  # Write data channel
                "BVALID", "BREADY", "BRESP",           # Write response channel
                "ARVALID", "ARADDR", "ARREADY",        # Read address channel
                "RVALID", "RREADY", "RRESP", "RDATA"]  # Read data channel

    def __init__(self, entity, name, clock, **kwargs):
        BusDriver.__init__(self, entity, name, clock, **kwargs)

        # Drive some sensible defaults (setimmediatevalue to avoid x asserts)
        self.bus.AWVALID.setimmediatevalue(0)
        self.bus.WVALID.setimmediatevalue(0)
        self.bus.ARVALID.setimmediatevalue(0)
        self.bus.BREADY.setimmediatevalue(1)
        self.bus.RREADY.setimmediatevalue(1)

        # Mutex for each channel that we master to prevent contention
        self.write_address_busy = Lock("%s_wabusy" % name)
        self.read_address_busy = Lock("%s_rabusy" % name)
        self.write_data_busy = Lock("%s_wbusy" % name)

    @cocotb.coroutine
    def _send_write_address(self, address, delay=0):
        """
        Send the write address, with optional delay (in clocks)
        """
        yield self.write_address_busy.acquire()
        for cycle in range(delay):
            yield RisingEdge(self.clock)

        self.bus.AWADDR <= address
        self.bus.AWVALID <= 1

        while True:
            yield ReadOnly()
            if self.bus.AWREADY.value:
                break
            yield RisingEdge(self.clock)
        yield RisingEdge(self.clock)
        self.bus.AWVALID <= 0
        self.write_address_busy.release()

    @cocotb.coroutine
    def _send_write_data(self, data, delay=0, byte_enable=0xF):
        """Send the write address, with optional delay (in clocks)."""
        yield self.write_data_busy.acquire()
        for cycle in range(delay):
            yield RisingEdge(self.clock)

        self.bus.WDATA <= data
        self.bus.WVALID <= 1
        self.bus.WSTRB <= byte_enable

        while True:
            yield ReadOnly()
            if self.bus.WREADY.value:
                break
            yield RisingEdge(self.clock)
        yield RisingEdge(self.clock)
        self.bus.WVALID <= 0
        self.write_data_busy.release()

    @cocotb.coroutine
    def write(self, address, value, byte_enable=0xf, address_latency=0,
              data_latency=0, sync=True):
        """Write a value to an address.

        Args:
            address (int): The address to write to.
            value (int): The data value to write.
            byte_enable (int, optional): Which bytes in value to actually write.
                Default is to write all bytes.
            address_latency (int, optional): Delay before setting the address (in clock cycles).
                Default is no delay.
            data_latency (int, optional): Delay before setting the data value (in clock cycles).
                Default is no delay.
            sync (bool, optional): Wait for rising edge on clock initially.
                Defaults to True.

        Returns:
            BinaryValue: The write response value.

        Raises:
            AXIProtocolError: If write response from AXI is not ``OKAY``.
        """
        if sync:
            yield RisingEdge(self.clock)

        c_addr = cocotb.fork(self._send_write_address(address,
                                                      delay=address_latency))
        c_data = cocotb.fork(self._send_write_data(value,
                                                   byte_enable=byte_enable,
                                                   delay=data_latency))

        if c_addr:
            yield c_addr.join()
        if c_data:
            yield c_data.join()

        # Wait for the response
        while True:
            yield ReadOnly()
            if self.bus.BVALID.value and self.bus.BREADY.value:
                result = self.bus.BRESP.value
                break
            yield RisingEdge(self.clock)

        yield RisingEdge(self.clock)

        if int(result):
            raise AXIProtocolError("Write to address 0x%08x failed with BRESP: %d"
                               % (address, int(result)))

        raise ReturnValue(result)

    @cocotb.coroutine
    def read(self, address, sync=True):
        """Read from an address.

        Args:
            address (int): The address to read from.
            sync (bool, optional): Wait for rising edge on clock initially.
                Defaults to True.

        Returns:
            BinaryValue: The read data value.

        Raises:
            AXIProtocolError: If read response from AXI is not ``OKAY``.
        """
        if sync:
            yield RisingEdge(self.clock)

        self.bus.ARADDR <= address
        self.bus.ARVALID <= 1

        while True:
            yield ReadOnly()
            if self.bus.ARREADY.value:
                break
            yield RisingEdge(self.clock)

        yield RisingEdge(self.clock)
        self.bus.ARVALID <= 0

        while True:
            yield ReadOnly()
            if self.bus.RVALID.value and self.bus.RREADY.value:
                data = self.bus.RDATA.value
                result = self.bus.RRESP.value
                break
            yield RisingEdge(self.clock)

        if int(result):
            raise AXIProtocolError("Read address 0x%08x failed with RRESP: %d" %
                               (address, int(result)))

        raise ReturnValue(data)

    def __len__(self):
        return 2**len(self.bus.ARADDR)


@cocotb.coroutine
def handshake(clock, drive, listen, delay=-1):
    """ Wait for a valid handshake on the supplied AXI signals

    `drive` and `listen` are the valid and ready signals for a given AXI
    channel depending on which direction this handshake is occuring. This
    coroutine will drive `drive` and wait for `listen`.

    `delay` specifies the clock cycles to wait before asserting drive
    after the master asserts listen.
        delay < 0: drive is asserted before listen.
        delay = 0: drive asserted combinatorially with listen.
        delay > 0: wait 'delay' clock cycles after listen to assert drive.
    """
    drive <= int(delay < 0)

    # check if listen is already asserted
    if not listen.value:
        yield RisingEdge(listen)

    # artificial delay
    for i in range(delay):
        yield RisingEdge(clock)

    # handshake - either drive or listen may already be asserted
    drive <= 1
    yield RisingEdge(clock)
    while not listen.value:
        yield RisingEdge(clock)
    drive <= 0


class AXI4Slave(BusDriver):
    """AXI4 Slave
    """
    _signals = [
        "ARID", "ARADDR", "ARLEN", "ARSIZE", "ARBURST", "ARVALID", "ARREADY",
        "AWID", "AWADDR", "AWLEN", "AWSIZE", "AWBURST", "AWVALID", "AWREADY",
        "WID", "WDATA", "WSTRB", "WLAST", "WVALID", "WREADY",
        "RID", "RDATA", "RRESP", "RLAST", "RVALID", "RREADY",
        "BID", "BRESP", "BVALID",  "BREADY",
    ]

    # Not currently supported by this driver
    _optional_signals = [
        "ARLOCK", "ARCACHE", "ARPROT", "ARQOS", "ARREGION", "ARUSER",
        "AWLOCK", "AWCACHE", "ARPROT", "AWQOS", "AWREGION", "AWUSER",
        "WUSER", "RUSER", "BUSER",
    ]

    def __init__(self, entity, name, clock, max_threads=1,
                awready_delay=-1, wready_delay=1, bresp_delay=1,
                arready_delay=-1, rresp_delay=1, **kwargs):
        BusDriver.__init__(self, entity, name, clock, **kwargs)
        self.clock = clock

        self.bus.RVALID <= 0
        self.bus.RLAST <= 0
        self.bus.BVALID <= 0
        self.bus.BID <= 0

        self.awready_delay = awready_delay
        self.wready_delay = wready_delay
        self.arready_delay = arready_delay
        assert bresp_delay > 0, "bresp_delay < 1 not supported"
        self.bresp_delay = bresp_delay
        assert rresp_delay > 0, "rresp_delay < 1 not supported"
        self.rresp_delay = rresp_delay

        self._bus_width = (
            abs(self.bus.WDATA._range[0] - self.bus.WDATA._range[1]) + 1) // 8

        assert self._bus_width in [2**n for n in range(8)], \
            "Unsupported Bus Width"

        self.max_threads = max_threads
        self._write_threads = []
        self._read_threads = []

        self.bresp_lock = Lock("%s_bresp_lock" % name)
        self.rresp_lock = Lock("%s_rresp_lock" % name)

        cocotb.fork(self._read_transaction())
        cocotb.fork(self._write_transaction())

    @cocotb.coroutine
    def _write_address(self):
        """Monitor the Write Address channel for transactions
        """
        yield handshake(self.clock,
                             self.bus.AWREADY,
                             self.bus.AWVALID,
                             self.awready_delay)

        awaddr = int(self.bus.AWADDR)
        awlen = int(self.bus.AWLEN)
        awsize = int(self.bus.AWSIZE)
        awburst = int(self.bus.AWBURST)
        awid = int(self.bus.AWID)

        raise ReturnValue((awaddr, awlen, awsize, awburst, awid))

    @cocotb.coroutine
    def _write_data(self):
        """Monitor the Write Data channel for transactions
        """
        last = 0
        wdata = []
        wstrb = []
        while not last:
            yield handshake(self.clock,
                                 self.bus.WREADY,
                                 self.bus.WVALID,
                                 self.wready_delay)

            wdata.append(int(self.bus.WDATA))
            wstrb.append(int(self.bus.WSTRB))
            last = int(self.bus.WLAST)
            wid = int(self.bus.WID)  # should be the same for each beat

        raise ReturnValue((wdata, wid, wstrb))

    @cocotb.coroutine
    def _write_transaction(self):
        """Process write transactions

        This requires both wdata and awaddr to complete.
        """
        while True:
            # Wait for wdata and awaddr
            data = cocotb.fork(self._write_data())
            addr = cocotb.fork(self._write_address())
            wdata, wid, wstrb = yield data.join()
            awaddr, awlen, awsize, awburst, awid = yield addr.join()

            self.log.debug(
                "Write Transaction:\n"
                "\t0x{:08X} <= {}"
                .format(
                    awaddr,
                    "\n\t{:14}".format('').join(
                        "0x{:016X}".format(d) for d in wdata
                    )
                )
            )

            cocotb.fork(self._write_response(
                awaddr, awlen, awsize, awburst, awid,
                wdata, wid, wstrb))

            # delay here until a thread is free
            while len(self._write_threads) >= self.max_threads:
                yield RisingEdge(self.clock)

    @cocotb.coroutine
    def _write_response(self, awaddr, awlen, awsize,
                        awburst, awid, wdata, wid, wstrb):
        """Wait for a write response
        """
        bresp = 0
        bresp_delay = self.bresp_delay
        try:
            assert awid == wid, "WID doesn't match AWID"
            assert awid not in self._write_threads, \
                "Thread ID already in progress"
            self._write_threads.append(awid)

            yield self._data_transfer(awaddr, 2**awsize, awlen + 1,
                                      awburst, wdata, wstrb)
        except Exception as e:
            self.log.warning("SAXI Error: {}".format(str(e)))
            bresp = 2
            bresp_delay = 1

        for i in range(bresp_delay-1):
            yield RisingEdge(self.clock)

        yield self.bresp_lock.acquire()
        self.bus.BID <= awid
        self.bus.BRESP <= bresp
        yield handshake(self.clock, self.bus.BVALID, self.bus.BREADY)
        self.bresp_lock.release()

        if awid in self._write_threads:
            self._write_threads.remove(awid)

    @cocotb.coroutine
    def _read_transaction(self):
        """Process a read transaction
        """
        while True:
            yield handshake(self.clock,
                            self.bus.ARREADY,
                            self.bus.ARVALID,
                            self.arready_delay)

            araddr = int(self.bus.ARADDR)
            arlen = int(self.bus.ARLEN)
            arsize = int(self.bus.ARSIZE)
            arburst = int(self.bus.ARBURST)
            arid = int(self.bus.ARID)

            cocotb.fork(self._read_response(
                    araddr, arlen, arsize, arburst, arid))

            # delay here until a thread is free
            while len(self._read_threads) >= self.max_threads:
                yield RisingEdge(self.clock)

    @cocotb.coroutine
    def _read_response(self, araddr, arlen, arsize, arburst, arid):
        """Wait for a read response, return the data transferred.
        """
        rresp = 0
        rresp_delay = self.rresp_delay
        try:
            assert arid not in self._read_threads, \
                "Thread ID already in progress"
            self._read_threads.append(arid)

            data = yield self._data_transfer(araddr, 2**arsize, arlen + 1,
                                             arburst)
        except Exception as e:
            self.log.warning("SAXI Error: {}".format(str(e)))
            rresp = 2
            rresp_delay = 1
            data = [0]

        for i in range(rresp_delay-1):
            yield RisingEdge(self.clock)

        yield self.rresp_lock.acquire()
        for i, d in enumerate(data):
            self.bus.RID <= arid
            self.bus.RRESP <= rresp
            self.bus.RDATA <= d
            self.bus.RLAST <= (1 if i == len(data)-1 else 0)
            yield handshake(self.clock, self.bus.RVALID, self.bus.RREADY)
            self.bus.RLAST <= 0
        self.rresp_lock.release()

        if arid in self._read_threads:
            self._read_threads.remove(arid)

    @cocotb.coroutine
    def _data_transfer(self, start_address, num_bytes, burst_length, mode,
                       data=None, strbs=None):
        """Perform AXI4 Data Transfer

        This method is basically the pseudocode from A3.4.2 of the Protocol
        Specification
        """
        # [FIXED, INCR, WRAP]
        assert mode in [0, 1, 2], "Unsupported Burst Mode:0x{:1X}".format(mode)

        if data is None or strbs is None:
            is_write = False
            data = []
        else:
            is_write = True
            assert len(data) == burst_length, \
                "Data supplied doesn't match burst_length"
            assert len(strbs) == burst_length, \
                "Data supplied doesn't match burst_length"

        addr = start_address
        aligned_address = (addr // num_bytes) * num_bytes
        aligned = aligned_address == addr
        dtsize = num_bytes * burst_length
        lower_wrap_boundary = (addr // dtsize) * dtsize
        upper_wrap_boundary = lower_wrap_boundary + dtsize

        for i in range(burst_length):
            lower_byte_lane = addr - (addr // self._bus_width) \
                * self._bus_width
            if aligned:
                upper_byte_lane = lower_byte_lane + num_bytes - 1
            else:
                upper_byte_lane = aligned_address + num_bytes - 1 \
                                  - (addr // self._bus_width) * self._bus_width

            # TODO check strb matches data address alignment
            if is_write:
                data_bytes = int_to_bytes(data[i], self._bus_width, 'little')
                yield self.do_slave_write(addr,
                    data_bytes[lower_byte_lane:upper_byte_lane + 1])
            else:
                data_bytes = yield self.do_slave_read(addr,
                    lower_byte_lane, upper_byte_lane)
                # TODO not sure how these bytes are aligned, might need some
                # padding
                data.append(int_from_bytes(data_bytes, 'little'))

            if mode != 0:
                if aligned:
                    addr = addr + num_bytes
                    if mode == 2:  # WRAP
                        if addr >= upper_wrap_boundary:
                            addr = lower_wrap_boundary
                else:  # INCR
                    addr = addr + num_bytes
                    aligned = True

        raise ReturnValue(data)

    @cocotb.coroutine
    def do_slave_write(self, addr, data_bytes):
        """Perform action on a write transaction
        """
        return
        yield

    @cocotb.coroutine
    def do_slave_read(self, addr, low_byte, high_byte):
        """Perform action on a read transaction
        """
        raise ReturnValue(int_to_bytes(0, high_byte - low_byte + 1, 'little'))
        yield


class AXI4MemoryMap(AXI4Slave):
    """An example AXI4 driver that provides a simple memory block.
    """
    def __init__(self, size, *args, **kwargs):
        AXI4Slave.__init__(self, *args, **kwargs)
        self._memory = memoryview(bytearray(size))

    @cocotb.coroutine
    def do_slave_write(self, addr, data_bytes):
        self._memory[addr:addr + len(data_bytes)] = data_bytes

        return
        yield

    @cocotb.coroutine
    def do_slave_read(self, addr, low_byte, high_byte):
        data_bytes = self._memory[addr:addr + high_byte + 1].tobytes()
        raise ReturnValue(data_bytes[low_byte:high_byte + 1])
        yield
