# Copyright (c) 2014 Potential Ventures Ltd
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

import array
import collections.abc
import enum
import itertools
from typing import Any, List, Optional, Sequence, Tuple, Union

import cocotb
from cocotb.binary import BinaryValue
from cocotb.drivers import BusDriver
from cocotb.handle import SimHandleBase
from cocotb.triggers import ClockCycles, Combine, Lock, ReadOnly, RisingEdge


class AXIBurst(enum.IntEnum):
    FIXED = 0b00
    INCR = 0b01
    WRAP = 0b10


class AXIxRESP(enum.IntEnum):
    OKAY = 0b00
    EXOKAY = 0b01
    SLVERR = 0b10
    DECERR = 0b11


class AXIProtocolError(Exception):
    def __init__(self,  message: str, xresp: AXIxRESP):
        super().__init__(message)
        self.xresp = xresp


class AXIReadBurstLengthMismatch(Exception):
    pass


class AXI4Master(BusDriver):
    """AXI4 Master

    TODO: Kill all pending transactions if reset is asserted.
    """

    _signals = [
        "AWVALID", "AWADDR", "AWREADY", "AWID", "AWLEN", "AWSIZE", "AWBURST",
        "WVALID", "WREADY", "WDATA", "WSTRB",
        "BVALID", "BREADY", "BRESP", "BID",
        "ARVALID", "ARADDR", "ARREADY", "ARID", "ARLEN", "ARSIZE", "ARBURST",
        "RVALID", "RREADY", "RRESP", "RDATA", "RID", "RLAST"]

    _optional_signals = ["AWREGION", "AWLOCK", "AWCACHE", "AWPROT", "AWQOS",
                         "WLAST",
                         "ARREGION", "ARLOCK", "ARCACHE", "ARPROT", "ARQOS"]

    def __init__(self, entity: SimHandleBase, name: str, clock: SimHandleBase,
                 **kwargs: Any):
        BusDriver.__init__(self, entity, name, clock, **kwargs)

        # Drive some sensible defaults (setimmediatevalue to avoid x asserts)
        self.bus.AWVALID.setimmediatevalue(0)
        self.bus.WVALID.setimmediatevalue(0)
        self.bus.ARVALID.setimmediatevalue(0)
        self.bus.BREADY.setimmediatevalue(1)
        self.bus.RREADY.setimmediatevalue(1)

        # Set the default value (0) for the unsupported signals, which
        # translate to:
        #  * Transaction IDs to 0
        #  * Region identifier to 0
        #  * Normal (non-exclusive) access
        #  * Device non-bufferable access
        #  * Unprivileged, secure data access
        #  * No QoS
        unsupported_signals = [
            "AWID", "AWREGION", "AWLOCK", "AWCACHE", "AWPROT", "AWQOS",
            "ARID", "ARREGION", "ARLOCK", "ARCACHE", "ARPROT", "ARQOS"]
        for signal in unsupported_signals:
            try:
                getattr(self.bus, signal).setimmediatevalue(0)
            except AttributeError:
                pass

        # Mutex for each channel to prevent contention
        self.write_address_busy = Lock(name + "_awbusy")
        self.read_address_busy = Lock(name + "_arbusy")
        self.write_data_busy = Lock(name + "_wbusy")
        self.read_data_busy = Lock(name + "_rbusy")
        self.write_response_busy = Lock(name + "_bbusy")

    @staticmethod
    def _check_length(length: int, burst: AXIBurst) -> None:
        """Check that the provided burst length is valid."""
        if length <= 0:
            raise ValueError("Burst length must be a positive integer")

        if burst is AXIBurst.INCR:
            if length > 256:
                raise ValueError("Maximum burst length for INCR bursts is 256")
        elif burst is AXIBurst.WRAP:
            if length not in (1, 2, 4, 8, 16):
                raise ValueError("Burst length for WRAP bursts must be 1, 2, "
                                 "4, 8 or 16")
        else:
            if length > 16:
                raise ValueError("Maximum burst length for FIXED bursts is 16")

    @staticmethod
    def _check_size(size: int, data_bus_width: int) -> None:
        """Check that the provided transfer size is valid."""
        if size > data_bus_width:
            raise ValueError("Beat size ({} B) is larger than the bus width "
                             "({} B)".format(size, data_bus_width))
        elif size <= 0 or size & (size - 1) != 0:
            raise ValueError("Beat size must be a positive power of 2")

    @staticmethod
    def _check_4kB_boundary_crossing(address: int, burst: AXIBurst, size: int,
                                     length: int) -> None:
        """Check that the provided burst does not cross a 4kB boundary."""
        if burst is AXIBurst.INCR:
            last_address = address + size * (length - 1)
            if address & ~0xfff != last_address & ~0xfff:
                raise ValueError(
                    "INCR burst with start address {:#x} and last address "
                    "{:#x} crosses the 4kB boundary {:#x}, which is forbidden "
                    "in a single burst"
                    .format(address, last_address,
                            (address & ~0xfff) + 0x1000))

    async def _send_write_address(
        self, address: int, length: int, burst: AXIBurst, size: int,
        delay: int, sync: bool
    ) -> None:
        """Send the write address, with optional delay (in clocks)"""
        async with self.write_address_busy:
            if sync:
                await RisingEdge(self.clock)

            await ClockCycles(self.clock, delay)

            # Set the address and, if present on the bus, burst, length and
            # size
            self.bus.AWADDR <= address
            self.bus.AWVALID <= 1

            if hasattr(self.bus, "AWBURST"):
                self.bus.AWBURST <= burst.value

            if hasattr(self.bus, "AWLEN"):
                self.bus.AWLEN <= length - 1

            if hasattr(self.bus, "AWSIZE"):
                self.bus.AWSIZE <= size.bit_length() - 1

            # Wait until acknowledged
            while True:
                await ReadOnly()
                if self.bus.AWREADY.value:
                    break
                await RisingEdge(self.clock)
            await RisingEdge(self.clock)
            self.bus.AWVALID <= 0

    async def _send_write_data(
        self, address, data: Sequence[int], burst: AXIBurst, size: int,
        delay: int, byte_enable: Sequence[Optional[int]], sync: bool
    ) -> None:
        """Send the write data, with optional delay (in clocks)."""

        # Helper function for narrow bursts
        def mask_and_shift(value: int, block_size: int, block_num: int) -> int:
            return (value & (2**block_size - 1)) << (block_num * block_size)

        # [0x33221100, 0x77665544] --> [0x221100XX, 0x66554433]
        def unalign_data(
            data: Sequence[int], size_bits: int, shift: int
        ) -> List[int]:
            padded_data = (0,) + tuple(value for value in data)
            low_mask = 2**(size_bits - shift) - 1
            high_mask = (2**shift - 1) << (size_bits - shift)

            return [(padded_data[i] & high_mask) >> (size_bits - shift) |
                    (padded_data[i + 1] & low_mask) << shift
                    for i in range(len(data))]

        strobes = []
        byte_enable_iterator = iter(byte_enable)
        try:
            for i in range(len(data)):
                current_byte_enable = next(byte_enable_iterator)
                strobes.append(2**size - 1 if current_byte_enable is None
                               else current_byte_enable)
        except StopIteration:
            # Fill the remaining strobes with the last one if we have reached
            # the end of the iterator
            strobes += [strobes[-1]] * (len(data) - i)

        # Unalign the words and strobes (if unaligned and not FIXED)
        if address % size != 0:
            shift = (address % size) * 8
            if burst is AXIBurst.FIXED:
                data = [(word << shift) & (2**(size * 8) - 1) for word in data]
                strobes = \
                    [(strb << shift // 8) & (2**size - 1) for strb in strobes]
            else:
                data = unalign_data(data, size * 8, shift)
                strobes = unalign_data(strobes, size, address % size)

        async with self.write_data_busy:
            if sync:
                await RisingEdge(self.clock)

            wdata_bytes = len(self.bus.WDATA) // 8
            narrow_block = (address % wdata_bytes) // size

            for beat_num, (word, strobe) in enumerate(zip(data, strobes)):
                await ClockCycles(self.clock, delay)

                self.bus.WVALID <= 1
                self.bus.WDATA <= mask_and_shift(word, size * 8, narrow_block)
                self.bus.WSTRB <= mask_and_shift(strobe, size, narrow_block)

                if burst is not AXIBurst.FIXED:
                    narrow_block = (narrow_block + 1) % (wdata_bytes // size)

                if hasattr(self.bus, "WLAST"):
                    if beat_num == len(data) - 1:
                        self.bus.WLAST <= 1
                    else:
                        self.bus.WLAST <= 0

                while True:
                    await RisingEdge(self.clock)
                    if self.bus.WREADY.value:
                        break

                if beat_num == len(data) - 1:
                    self.bus.WVALID <= 0

    @cocotb.coroutine
    async def write(
        self, address: int, value: Union[int, Sequence[int]], *,
        size: Optional[int] = None, burst: AXIBurst = AXIBurst.INCR,
        byte_enable: Union[Optional[int], Sequence[Optional[int]]] = None,
        address_latency: int = 0, data_latency: int = 0, sync: bool = True
    ) -> None:
        """Write a value to an address.

        With unaligned writes (when ``address`` is not a multiple of ``size``),
        only the low ``size - address % size`` Bytes are written for:
        * the last element of ``value`` for INCR or WRAP bursts, or
        * every element of ``value`` for FIXED bursts.

        Args:
            address: The address to write to.
            value: The data value(s) to write.
            size: The size (in bytes) of each beat. Defaults to None (width of
                the data bus).
            burst: The burst type, either ``FIXED``, ``INCR`` or ``WRAP``.
                Defaults to ``INCR``.
            byte_enable: Which bytes in value to actually write. Defaults to
                None (write all bytes).
            address_latency: Delay before setting the address (in clock
                cycles). Default is no delay.
            data_latency: Delay before setting the data value (in clock
                cycles).
                Default is no delay.
            sync: Wait for rising edge on clock initially.
                Defaults to True.

        Raises:
            ValueError: If any of the input parameters is invalid.
            AXIProtocolError: If write response from AXI is not ``OKAY``.
        """

        if not isinstance(value, collections.abc.Sequence):
            value = (value,)    # If value is not a sequence, make it

        if not isinstance(byte_enable, collections.abc.Sequence):
            byte_enable = (byte_enable,)    # Same for byte_enable

        if size is None:
            size = len(self.bus.WDATA) // 8
        else:
            AXI4Master._check_size(size, len(self.bus.WDATA) // 8)

        AXI4Master._check_length(len(value), burst)
        AXI4Master._check_4kB_boundary_crossing(address, burst, size,
                                                len(value))

        write_address = self._send_write_address(address, len(value), burst,
                                                 size, address_latency, sync)

        write_data = self._send_write_data(address, value, burst, size,
                                           data_latency, byte_enable, sync)

        await Combine(cocotb.fork(write_address), cocotb.fork(write_data))

        async with self.write_response_busy:
            # Wait for the response
            while True:
                await ReadOnly()
                if self.bus.BVALID.value and self.bus.BREADY.value:
                    result = AXIxRESP(self.bus.BRESP.value.integer)
                    break
                await RisingEdge(self.clock)

            await RisingEdge(self.clock)

            if result is not AXIxRESP.OKAY:
                err_msg = "Write to address {0:#x}"
                if len(value) != 1:
                    err_msg += " ({1} beats, {2} burst)"
                err_msg += " failed with BRESP: {3} ({4})"

                raise AXIProtocolError(
                    err_msg.format(address, len(value), burst.name,
                                   result.value, result.name), result)

    @cocotb.coroutine
    async def read(
        self, address: int, length: int = 1, *,
        size: Optional[int] = None, burst: AXIBurst = AXIBurst.INCR,
        return_rresp: bool = False, sync: bool = True
    ) -> Union[List[BinaryValue], List[Tuple[BinaryValue, AXIxRESP]]]:
        """Read from an address.

        With unaligned reads (when ``address`` is not a multiple of ``size``)
        with INCR or WRAP bursts, the last element of the returned read data
        will be only the low-order ``size - address % size`` Bytes of the last
        word.
        With unaligned reads with FIXED bursts, every element of the returned
        read data will be only the low-order ``size - address % size`` Bytes.

        Args:
            address: The address to read from.
            length: Number of words to transfer. Defaults to 1.
            size: The size (in bytes) of each beat. Defaults to None (width of
                the data bus).
            burst: The burst type, either ``FIXED``, ``INCR`` or ``WRAP``.
                Defaults to ``INCR``.
            return_rresp: Return the list of RRESP values, instead of raising
                an AXIProtocolError in case of not OKAY. Defaults to False.
            sync: Wait for rising edge on clock initially. Defaults to True.

        Returns:
            The read data values or, if *return_rresp* is True, a list of pairs
            each containing the data and RRESP values.-

        Raises:
            ValueError: If any of the input parameters is invalid.
            AXIProtocolError: If read response from AXI is not ``OKAY`` and
                *return_rresp* is False
            AXIReadBurstLengthMismatch: If the received number of words does
                not match the requested one.
        """

        # Helper function for narrow bursts
        def shift_and_mask(binvalue: BinaryValue, bytes_num: int,
                           byte_shift: int) -> BinaryValue:
            start = byte_shift * 8
            end = (bytes_num + byte_shift) * 8
            return binvalue[len(binvalue) - end:len(binvalue) - start - 1]

        # [0x221100XX, 0x66554433] --> [0x33221100, 0x665544]
        def realign_data(
            data: Sequence[BinaryValue], size_bits: int, shift: int
        ) -> List[BinaryValue]:
            binstr_join = "".join([word.binstr[::-1] for word in data])
            binstr_join = binstr_join[shift:]
            data_binstr = [binstr_join[i * size_bits:(i + 1) * size_bits][::-1]
                           for i in range(len(data))]
            return [BinaryValue(value=binstr, n_bits=len(binstr))
                    for binstr in data_binstr]

        if size is None:
            size = len(self.bus.RDATA) // 8
        else:
            AXI4Master._check_size(size, len(self.bus.RDATA) // 8)

        AXI4Master._check_length(length, burst)
        AXI4Master._check_4kB_boundary_crossing(address, burst, size, length)

        rdata_bytes = len(self.bus.RDATA) // 8
        byte_offset = (address % rdata_bytes) // size * size

        async with self.read_address_busy:
            if sync:
                await RisingEdge(self.clock)

            self.bus.ARADDR <= address
            self.bus.ARVALID <= 1

            if hasattr(self.bus, "ARLEN"):
                self.bus.ARLEN <= length - 1

            if hasattr(self.bus, "ARSIZE"):
                self.bus.ARSIZE <= size.bit_length() - 1

            if hasattr(self.bus, "ARBURST"):
                self.bus.ARBURST <= burst.value

            while True:
                await ReadOnly()
                if self.bus.ARREADY.value:
                    break
                await RisingEdge(self.clock)

            await RisingEdge(self.clock)
            self.bus.ARVALID <= 0

        async with self.read_data_busy:
            data = []
            rresp = []

            for beat_num in itertools.count():
                while True:
                    await ReadOnly()
                    if self.bus.RVALID.value and self.bus.RREADY.value:
                        # Shift and mask to correctly handle narrow bursts
                        beat_value = shift_and_mask(self.bus.RDATA.value,
                                                    size, byte_offset)

                        data.append(beat_value)
                        rresp.append(AXIxRESP(self.bus.RRESP.value.integer))

                        if burst is not AXIBurst.FIXED:
                            byte_offset = (byte_offset + size) % rdata_bytes

                        break
                    await RisingEdge(self.clock)

                if not hasattr(self.bus, "RLAST") or self.bus.RLAST.value:
                    break

                await RisingEdge(self.clock)

            await RisingEdge(self.clock)

            if len(data) != length:
                raise AXIReadBurstLengthMismatch(
                    "AXI4 slave returned {} data than expected (requested {} "
                    "words, received {})"
                    .format("more" if len(data) > length else "less",
                            length, len(data)))

            # Re-align the words
            if address % size != 0:
                shift = (address % size) * 8
                if burst is AXIBurst.FIXED:
                    data = [word[0:size * 8 - shift - 1] for word in data]
                else:
                    data = realign_data(data, size * 8, shift)

            if return_rresp:
                return list(zip(data, rresp))
            else:
                for beat_number, beat_result in enumerate(rresp):
                    if beat_result is not AXIxRESP.OKAY:
                        err_msg = "Read on address {0:#x}"
                        if length != 1:
                            err_msg += " (beat {1} of {2}, {3} burst)"
                        err_msg += " failed with RRESP: {4} ({5})"

                        err_msg = err_msg.format(
                            address, beat_number + 1, length, burst,
                            beat_result.value, beat_result.name)

                        raise AXIProtocolError(err_msg, beat_result)

                return data

    def __len__(self):
        return 2**len(self.bus.ARADDR)


class AXI4LiteMaster(AXI4Master):
    """AXI4-Lite Master"""

    _signals = ["AWVALID", "AWADDR", "AWREADY",        # Write address channel
                "WVALID", "WREADY", "WDATA", "WSTRB",  # Write data channel
                "BVALID", "BREADY", "BRESP",           # Write response channel
                "ARVALID", "ARADDR", "ARREADY",        # Read address channel
                "RVALID", "RREADY", "RRESP", "RDATA"]  # Read data channel

    _optional_signals = []

    @cocotb.coroutine
    async def write(
        self, address: int, value: int, byte_enable: Optional[int] = None,
        address_latency: int = 0, data_latency: int = 0, sync: bool = True
    ) -> BinaryValue:
        """Write a value to an address.

        Args:
            address: The address to write to.
            value: The data value to write.
            byte_enable: Which bytes in value to actually write. Defaults to
                None (write all bytes).
            address_latency: Delay before setting the address (in clock
                cycles). Default is no delay.
            data_latency: Delay before setting the data value (in clock
                cycles). Default is no delay.
            sync: Wait for rising edge on clock initially. Defaults to True.

            Returns:
                The write response value.

            Raises:
                ValueError: If any of the input parameters is invalid.
                AXIProtocolError: If write response from AXI is not ``OKAY``.
        """

        if isinstance(value, collections.abc.Sequence):
            raise ValueError("AXI4-Lite does not support burst transfers")

        await super().write(
            address=address, value=value, size=None, burst=AXIBurst.INCR,
            byte_enable=byte_enable, address_latency=address_latency,
            data_latency=data_latency, sync=sync)

        # Needed for backwards compatibility
        return BinaryValue(value=AXIxRESP.OKAY.value, n_bits=2)

    @cocotb.coroutine
    async def read(self, address: int, sync: bool = True) -> BinaryValue:
        """Read from an address.

        Args:
            address: The address to read from.
            length: Number of words to transfer
            sync: Wait for rising edge on clock initially. Defaults to True.

        Returns:
            The read data value.

        Raises:
            AXIProtocolError: If read response from AXI is not ``OKAY``.
        """

        ret = await super().read(address=address, length=1, size=None,
                                 burst=AXIBurst.INCR, return_rresp=False,
                                 sync=sync)
        return ret[0]


class AXI4Slave(BusDriver):
    '''
    AXI4 Slave

    Monitors an internal memory and handles read and write requests.
    '''
    _signals = [
        "ARREADY", "ARVALID", "ARADDR",             # Read address channel
        "ARLEN",   "ARSIZE",  "ARBURST", "ARPROT",

        "RREADY",  "RVALID",  "RDATA",   "RLAST",   # Read response channel

        "AWREADY", "AWADDR",  "AWVALID",            # Write address channel
        "AWPROT",  "AWSIZE",  "AWBURST", "AWLEN",

        "WREADY",  "WVALID",  "WDATA",

    ]

    # Not currently supported by this driver
    _optional_signals = [
        "WLAST",   "WSTRB",
        "BVALID",  "BREADY",  "BRESP",   "RRESP",
        "RCOUNT",  "WCOUNT",  "RACOUNT", "WACOUNT",
        "ARLOCK",  "AWLOCK",  "ARCACHE", "AWCACHE",
        "ARQOS",   "AWQOS",   "ARID",    "AWID",
        "BID",     "RID",     "WID"
    ]

    def __init__(self, entity, name, clock, memory, callback=None, event=None,
                 big_endian=False, **kwargs):

        BusDriver.__init__(self, entity, name, clock, **kwargs)
        self.clock = clock

        self.big_endian = big_endian
        self.bus.ARREADY.setimmediatevalue(1)
        self.bus.RVALID.setimmediatevalue(0)
        self.bus.RLAST.setimmediatevalue(0)
        self.bus.AWREADY.setimmediatevalue(1)
        self._memory = memory

        self.write_address_busy = Lock("%s_wabusy" % name)
        self.read_address_busy = Lock("%s_rabusy" % name)
        self.write_data_busy = Lock("%s_wbusy" % name)

        cocotb.fork(self._read_data())
        cocotb.fork(self._write_data())

    def _size_to_bytes_in_beat(self, AxSIZE):
        if AxSIZE < 7:
            return 2 ** AxSIZE
        return None

    async def _write_data(self):
        clock_re = RisingEdge(self.clock)

        while True:
            while True:
                self.bus.WREADY <= 0
                await ReadOnly()
                if self.bus.AWVALID.value:
                    self.bus.WREADY <= 1
                    break
                await clock_re

            await ReadOnly()
            _awaddr = int(self.bus.AWADDR)
            _awlen = int(self.bus.AWLEN)
            _awsize = int(self.bus.AWSIZE)
            _awburst = int(self.bus.AWBURST)
            _awprot = int(self.bus.AWPROT)

            burst_length = _awlen + 1
            bytes_in_beat = self._size_to_bytes_in_beat(_awsize)

            if __debug__:
                self.log.debug(
                    "AWADDR  %d\n" % _awaddr +
                    "AWLEN   %d\n" % _awlen +
                    "AWSIZE  %d\n" % _awsize +
                    "AWBURST %d\n" % _awburst +
                    "AWPROT %d\n" % _awprot +
                    "BURST_LENGTH %d\n" % burst_length +
                    "Bytes in beat %d\n" % bytes_in_beat)

            burst_count = burst_length

            await clock_re

            while True:
                if self.bus.WVALID.value:
                    word = self.bus.WDATA.value
                    word.big_endian = self.big_endian
                    _burst_diff = burst_length - burst_count
                    _st = _awaddr + (_burst_diff * bytes_in_beat)  # start
                    _end = _awaddr + ((_burst_diff + 1) * bytes_in_beat)  # end
                    self._memory[_st:_end] = array.array('B', word.buff)
                    burst_count -= 1
                    if burst_count == 0:
                        break
                await clock_re

    async def _read_data(self):
        clock_re = RisingEdge(self.clock)

        while True:
            while True:
                await ReadOnly()
                if self.bus.ARVALID.value:
                    break
                await clock_re

            await ReadOnly()
            _araddr = int(self.bus.ARADDR)
            _arlen = int(self.bus.ARLEN)
            _arsize = int(self.bus.ARSIZE)
            _arburst = int(self.bus.ARBURST)
            _arprot = int(self.bus.ARPROT)

            burst_length = _arlen + 1
            bytes_in_beat = self._size_to_bytes_in_beat(_arsize)

            word = BinaryValue(n_bits=bytes_in_beat*8, bigEndian=self.big_endian)

            if __debug__:
                self.log.debug(
                    "ARADDR  %d\n" % _araddr +
                    "ARLEN   %d\n" % _arlen +
                    "ARSIZE  %d\n" % _arsize +
                    "ARBURST %d\n" % _arburst +
                    "ARPROT %d\n" % _arprot +
                    "BURST_LENGTH %d\n" % burst_length +
                    "Bytes in beat %d\n" % bytes_in_beat)

            burst_count = burst_length

            await clock_re

            while True:
                self.bus.RVALID <= 1
                await ReadOnly()
                if self.bus.RREADY.value:
                    _burst_diff = burst_length - burst_count
                    _st = _araddr + (_burst_diff * bytes_in_beat)
                    _end = _araddr + ((_burst_diff + 1) * bytes_in_beat)
                    word.buff = self._memory[_st:_end].tobytes()
                    self.bus.RDATA <= word
                    if burst_count == 1:
                        self.bus.RLAST <= 1
                await clock_re
                burst_count -= 1
                self.bus.RLAST <= 0
                if burst_count == 0:
                    break
