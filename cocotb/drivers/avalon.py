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

"""Drivers for Intel Avalon interfaces.

See https://www.intel.com/content/dam/www/programmable/us/en/pdfs/literature/manual/mnl_avalon_spec_1_3.pdf

NB Currently we only support a very small subset of functionality
"""

import random

import cocotb
from cocotb.decorators import coroutine
from cocotb.triggers import RisingEdge, FallingEdge, ReadOnly, NextTimeStep, Event
from cocotb.drivers import BusDriver, ValidatedBusDriver
from cocotb.utils import hexdump
from cocotb.binary import BinaryValue
from cocotb.result import ReturnValue, TestError


class AvalonMM(BusDriver):
    """Avalon Memory Mapped Interface (Avalon-MM) Driver.

    Currently we only support the mode required to communicate with SF
    avalon_mapper which is a limited subset of all the signals.

    Blocking operation is all that is supported at the moment, and for the near
    future as well.
    Posted responses from a slave are not supported.
    """
    _signals = ["address"]
    _optional_signals = ["readdata", "read", "write", "waitrequest",
                         "writedata", "readdatavalid", "byteenable",
                         "cs"]


    def __init__(self, entity, name, clock, **kwargs):
        BusDriver.__init__(self, entity, name, clock, **kwargs)
        self._can_read = False
        self._can_write = False

        # Drive some sensible defaults (setimmediatevalue to avoid x asserts)
        if hasattr(self.bus, "read"):
            self.bus.read.setimmediatevalue(0)
            self._can_read = True

        if hasattr(self.bus, "write"):
            self.bus.write.setimmediatevalue(0)
            v = self.bus.writedata.value
            v.binstr = "x" * len(self.bus.writedata)
            self.bus.writedata <= v
            self._can_write = True

        if hasattr(self.bus, "byteenable"):
            self.bus.byteenable.setimmediatevalue(0)

        if hasattr(self.bus, "cs"):
            self.bus.cs.setimmediatevalue(0)

        v = self.bus.address.value
        v.binstr = "x" * len(self.bus.address)
        self.bus.address.setimmediatevalue(v)

    def read(self, address):
        pass

    def write(self, address, value):
        pass


class AvalonMaster(AvalonMM):
    """Avalon Memory Mapped Interface (Avalon-MM) Master"""
    def __init__(self, entity, name, clock, **kwargs):
        AvalonMM.__init__(self, entity, name, clock, **kwargs)
        self.log.debug("AvalonMaster created")
        self.busy_event = Event("%s_busy" % name)
        self.busy = False

    def __len__(self):
        return 2**len(self.bus.address)

    @coroutine
    def _acquire_lock(self):
        if self.busy:
            yield self.busy_event.wait()
        self.busy_event.clear()
        self.busy = True

    def _release_lock(self):
        self.busy = False
        self.busy_event.set()

    @coroutine
    def read(self, address, sync=True):
        """Issue a request to the bus and block until this
        comes back. Simulation time still progresses
        but syntactically it blocks.

        Args:
            address (int): The address to read from.
            sync (bool, optional): Wait for rising edge on clock initially.
                Defaults to True.

        Returns:
            BinaryValue: The read data value.

        Raises:
            :any:`TestError`: If master is write-only.
        """
        if not self._can_read:
            self.log.error("Cannot read - have no read signal")
            raise TestError("Attempt to read on a write-only AvalonMaster")

        yield self._acquire_lock()

        # Apply values for next clock edge
        if sync:
            yield RisingEdge(self.clock)
        self.bus.address <= address
        self.bus.read <= 1
        if hasattr(self.bus, "byteenable"):
            self.bus.byteenable <= int("1"*len(self.bus.byteenable), 2)
        if hasattr(self.bus, "cs"):
            self.bus.cs <= 1

        # Wait for waitrequest to be low
        if hasattr(self.bus, "waitrequest"):
            yield self._wait_for_nsignal(self.bus.waitrequest)
        yield RisingEdge(self.clock)

        # Deassert read
        self.bus.read <= 0
        if hasattr(self.bus, "byteenable"):
            self.bus.byteenable <= 0
        if hasattr(self.bus, "cs"):
            self.bus.cs <= 0
        v = self.bus.address.value
        v.binstr = "x" * len(self.bus.address)
        self.bus.address <= v

        if hasattr(self.bus, "readdatavalid"):
            while True:
                yield ReadOnly()
                if int(self.bus.readdatavalid):
                    break
                yield RisingEdge(self.clock)
        else:
            # Assume readLatency = 1 if no readdatavalid
            # FIXME need to configure this,
            # should take a dictionary of Avalon properties.
            yield ReadOnly()

        # Get the data
        data = self.bus.readdata.value

        self._release_lock()
        raise ReturnValue(data)

    @coroutine
    def write(self, address, value):
        """Issue a write to the given address with the specified
        value.

        Args:
            address (int): The address to write to.
            value (int): The data value to write.

        Raises:
            :any:`TestError`: If master is read-only.
        """
        if not self._can_write:
            self.log.error("Cannot write - have no write signal")
            raise TestError("Attempt to write on a read-only AvalonMaster")

        yield self._acquire_lock()

        # Apply values to bus
        yield RisingEdge(self.clock)
        self.bus.address <= address
        self.bus.writedata <= value
        self.bus.write <= 1
        if hasattr(self.bus, "byteenable"):
            self.bus.byteenable <= int("1"*len(self.bus.byteenable), 2)
        if hasattr(self.bus, "cs"):
            self.bus.cs <= 1

        # Wait for waitrequest to be low
        if hasattr(self.bus, "waitrequest"):
            count = yield self._wait_for_nsignal(self.bus.waitrequest)

        # Deassert write
        yield RisingEdge(self.clock)
        self.bus.write <= 0
        if hasattr(self.bus, "byteenable"):
            self.bus.byteenable <= 0
        if hasattr(self.bus, "cs"):
            self.bus.cs <= 0
        v = self.bus.address.value
        v.binstr = "x" * len(self.bus.address)
        self.bus.address <= v

        v = self.bus.writedata.value
        v.binstr = "x" * len(self.bus.writedata)
        self.bus.writedata <= v
        self._release_lock()


class AvalonMemory(BusDriver):
    """Emulate a memory, with back-door access."""
    _signals = ["address"]
    _optional_signals = ["write", "read", "writedata", "readdatavalid",
                         "readdata", "waitrequest", "burstcount", "byteenable"]
    _avalon_properties = {
            "burstCountUnits": "symbols",  # symbols or words
            "addressUnits": "symbols",     # symbols or words
            "readLatency": 1,    # number of cycles
            "WriteBurstWaitReq": True,  # generate random waitrequest
            "MaxWaitReqLen": 4,  # maximum value of waitrequest
            }

    def __init__(self, entity, name, clock, readlatency_min=1,
                 readlatency_max=1, memory=None, avl_properties={}):
        BusDriver.__init__(self, entity, name, clock)

        if avl_properties != {}:
            for key, value in self._avalon_properties.items():
                self._avalon_properties[key] = avl_properties.get(key, value)

        if self._avalon_properties["burstCountUnits"] != "symbols":
            self.log.error("Only symbols burstCountUnits is supported")

        if self._avalon_properties["addressUnits"] != "symbols":
            self.log.error("Only symbols addressUnits is supported")

        self._burstread = False
        self._burstwrite = False
        self._readable = False
        self._writeable = False
        self._width = None

        if hasattr(self.bus, "readdata"):
            self._width = len(self.bus.readdata)
            self.dataByteSize = int(self._width/8)
            self._readable = True

        if hasattr(self.bus, "writedata"):
            width = len(self.bus.writedata)
            if (self._width is not None) and self._width != width:
                self.log.error("readdata and writedata bus" +
                               " are not the same size")
            self._width = width
            self.dataByteSize = int(self._width/8)
            self._writeable = True

        if not self._readable and not self._writeable:
            raise TestError("Attempt to instantiate useless memory")

        # Allow dual port RAMs by referencing the same dictionary
        if memory is None:
            self._mem = {}
        else:
            self._mem = memory

        self._val = BinaryValue(n_bits=self._width, bigEndian=False)
        self._readlatency_min = readlatency_min
        self._readlatency_max = readlatency_max
        self._responses = []
        self._coro = cocotb.fork(self._respond())

        if hasattr(self.bus, "readdatavalid"):
            self.bus.readdatavalid.setimmediatevalue(0)

        if hasattr(self.bus, "waitrequest"):
            self.bus.waitrequest.setimmediatevalue(0)

        if hasattr(self.bus, "burstcount"):
            if hasattr(self.bus, "readdatavalid"):
                self._burstread = True
            self._burstwrite = True
            if self._avalon_properties.get("WriteBurstWaitReq", True):
                self.bus.waitrequest <= 1
            else:
                self.bus.waitrequest <= 0


        if hasattr(self.bus, "readdatavalid"):
            self.bus.readdatavalid.setimmediatevalue(0)

    def _pad(self):
        """Pad response queue up to read latency."""
        l = random.randint(self._readlatency_min, self._readlatency_max)
        while len(self._responses) < l:
            self._responses.append(None)

    def _do_response(self):
        if self._responses:
            resp = self._responses.pop(0)
        else:
            resp = None

        if resp is not None:
            if resp is True:
                self._val.binstr = "x" * self._width
            else:
                self._val.integer = resp
                self.log.debug("sending 0x%x (%s)" %
                               (self._val.integer, self._val.binstr))
            self.bus.readdata <= self._val
            if hasattr(self.bus, "readdatavalid"):
                self.bus.readdatavalid <= 1
        elif hasattr(self.bus, "readdatavalid"):
            self.bus.readdatavalid <= 0

    def _write_burst_addr(self):
        """Reading write burst address, burstcount, byteenable."""
        addr = self.bus.address.value.integer
        if addr % self.dataByteSize != 0:
            self.log.error("Address must be aligned to data width" +
                           "(addr = " + hex(addr) +
                           ", width = " + str(self._width))

        byteenable = self.bus.byteenable.value
        if byteenable != int("1"*len(self.bus.byteenable), 2):
            self.log.error("Only full word access is supported " +
                           "for burst write (byteenable must be " +
                           "0b" + "1" * len(self.bus.byteenable) +
                           ")")

        burstcount = self.bus.burstcount.value.integer
        if burstcount == 0:
            self.log.error("Write burstcount must be 1 at least")

        return (addr, byteenable, burstcount)

    @coroutine
    def _writing_byte_value(self, byteaddr):
        """Writing value in _mem with byteaddr size."""
        yield FallingEdge(self.clock)
        for i in range(self.dataByteSize):
            data = self.bus.writedata.value.integer
            addrtmp = byteaddr + i
            datatmp = (data >> (i*8)) & 0xff
            self._mem[addrtmp] = datatmp

    @coroutine
    def _waitrequest(self):
        """Generate waitrequest randomly."""
        if self._avalon_properties.get("WriteBurstWaitReq", True):
            if random.choice([True, False, False, False]):
                randmax = self._avalon_properties.get("MaxWaitReqLen", 0)
                waitingtime = range(random.randint(0, randmax))
                for waitreq in waitingtime:
                    self.bus.waitrequest <= 1
                    yield RisingEdge(self.clock)
            else:
                yield NextTimeStep()

            self.bus.waitrequest <= 0


    @coroutine
    def _respond(self):
        """Coroutine to respond to the actual requests."""
        edge = RisingEdge(self.clock)
        while True:
            yield edge
            self._do_response()

            yield ReadOnly()

            if self._readable and self.bus.read.value:
                if not self._burstread:
                    self._pad()
                    addr = self.bus.address.value.integer
                    if addr not in self._mem:
                        self.log.warning("Attempt to read from uninitialised "
                                         "address 0x%x", addr)
                        self._responses.append(True)
                    else:
                        self.log.debug("Read from address 0x%x returning 0x%x",
                                       addr, self._mem[addr])
                        self._responses.append(self._mem[addr])
                else:
                    addr = self.bus.address.value.integer
                    if addr % self.dataByteSize != 0:
                        self.log.error("Address must be aligned to data width" +
                                       "(addr = " + hex(addr) +
                                       ", width = " + str(self._width))
                    addr = int(addr / self.dataByteSize)
                    burstcount = self.bus.burstcount.value.integer
                    byteenable = self.bus.byteenable.value
                    if byteenable != int("1"*len(self.bus.byteenable), 2):
                        self.log.error("Only full word access is supported " +
                                       "for burst read (byteenable must be " +
                                       "0b" + "1" * len(self.bus.byteenable) +
                                       ")")
                    if burstcount == 0:
                        self.log.error("Burstcount must be 1 at least")

                    # toggle waitrequest
                    # TODO: configure waitrequest time with avalon properties
                    yield NextTimeStep()  # can't write during read-only phase
                    self.bus.waitrequest <= 1
                    yield edge
                    yield edge
                    self.bus.waitrequest <= 0

                    # wait for read data
                    for i in range(self._avalon_properties["readLatency"]):
                        yield edge
                    for count in range(burstcount):
                        if (addr + count)*self.dataByteSize not in self._mem:
                            self.log.warning("Attempt to burst read from uninitialised "
                                             "address 0x%x (addr 0x%x count 0x%x)",
                                             (addr + count) * self.dataByteSize, addr, count)
                            self._responses.append(True)
                        else:
                            value = 0
                            for i in range(self.dataByteSize):
                                rvalue = self._mem[(addr + count)*self.dataByteSize + i]
                                value += rvalue << i*8
                            self.log.debug("Read from address 0x%x returning 0x%x",
                                           (addr + count) * self.dataByteSize, value)
                            self._responses.append(value)
                        yield edge
                        self._do_response()

            if self._writeable and self.bus.write.value:
                if not self._burstwrite:
                    addr = self.bus.address.value.integer
                    data = self.bus.writedata.value.integer
                    if hasattr(self.bus, "byteenable"):
                        byteenable = int(self.bus.byteenable.value)
                        mask = 0
                        oldmask = 0
                        olddata = 0
                        if addr in self._mem:
                            olddata = self._mem[addr]
                        self.log.debug("Old Data  : %x", olddata)
                        self.log.debug("Data in   : %x", data)
                        self.log.debug("Width     : %d", self._width)
                        self.log.debug("Byteenable: %x", byteenable)
                        for i in range(self._width/8):
                            if byteenable & 2**i:
                                mask |= 0xFF << (8*i)
                            else:
                                oldmask |= 0xFF << (8*i)

                        self.log.debug("Data mask : %x", mask)
                        self.log.debug("Old mask  : %x", oldmask)

                        data = (data & mask) | (olddata & oldmask)

                        self.log.debug("Data out  : %x", data)

                    self.log.debug("Write to address 0x%x -> 0x%x", addr, data)
                    self._mem[addr] = data
                else:
                    self.log.debug("writing burst")
                    # maintain waitrequest high randomly
                    yield self._waitrequest()

                    addr, byteenable, burstcount = self._write_burst_addr()

                    for count in range(burstcount):
                        while self.bus.write.value == 0:
                            yield NextTimeStep()
                        # self._mem is aligned on 8 bits words
                        yield self._writing_byte_value(addr + count*self.dataByteSize)
                        self.log.debug("writing %016X @ %08X",
                                       self.bus.writedata.value.integer,
                                       addr + count * self.dataByteSize)
                        yield edge
                        # generate waitrequest randomly
                        yield self._waitrequest()

                    if self._avalon_properties.get("WriteBurstWaitReq", True):
                        self.bus.waitrequest <= 1


class AvalonST(ValidatedBusDriver):
    """Avalon Streaming Interface (Avalon-ST) Driver"""

    _signals = ["valid", "data"]
    _optional_signals = ["ready"]

    _default_config = {"firstSymbolInHighOrderBits" : True}

    def __init__(self, *args, **kwargs):
        config = kwargs.pop('config', {})
        ValidatedBusDriver.__init__(self, *args, **kwargs)

        self.config = AvalonST._default_config.copy()

        for configoption, value in config.items():
            self.config[configoption] = value
            self.log.debug("Setting config option %s to %s", configoption, str(value))

        word = BinaryValue(n_bits=len(self.bus.data), bigEndian=self.config["firstSymbolInHighOrderBits"],
                           value="x" * len(self.bus.data))

        self.bus.valid  <= 0
        self.bus.data   <= word

    @coroutine
    def _wait_ready(self):
        """Wait for a ready cycle on the bus before continuing.

            Can no longer drive values this cycle...

            FIXME assumes readyLatency of 0
        """
        yield ReadOnly()
        while not self.bus.ready.value:
            yield RisingEdge(self.clock)
            yield ReadOnly()

    @coroutine
    def _driver_send(self, value, sync=True):
        """Send a transmission over the bus.

        Args:
            value: data to drive onto the bus.
        """
        self.log.debug("Sending Avalon transmission: %r", value)

        # Avoid spurious object creation by recycling
        clkedge = RisingEdge(self.clock)

        word = BinaryValue(n_bits=len(self.bus.data), bigEndian=False)

        # Drive some defaults since we don't know what state we're in
        self.bus.valid <= 0

        if sync:
            yield clkedge

        # Insert a gap where valid is low
        if not self.on:
            self.bus.valid <= 0
            for _ in range(self.off):
                yield clkedge

            # Grab the next set of on/off values
            self._next_valids()

        # Consume a valid cycle
        if self.on is not True and self.on:
            self.on -= 1

        self.bus.valid <= 1

        word.assign(value)
        self.bus.data <= word

        # If this is a bus with a ready signal, wait for this word to
        # be acknowledged
        if hasattr(self.bus, "ready"):
            yield self._wait_ready()

        yield clkedge
        self.bus.valid <= 0
        word.binstr   = "x" * len(self.bus.data)
        self.bus.data <= word

        self.log.debug("Successfully sent Avalon transmission: %r", value)


class AvalonSTPkts(ValidatedBusDriver):
    """Avalon Streaming Interface (Avalon-ST) Driver, packetised."""

    _signals = ["valid", "data", "startofpacket", "endofpacket"]
    _optional_signals = ["error", "channel", "ready", "empty"]

    _default_config = {
        "dataBitsPerSymbol"             : 8,
        "firstSymbolInHighOrderBits"    : True,
        "maxChannel"                    : 0,
        "readyLatency"                  : 0
    }

    def __init__(self, *args, **kwargs):
        config = kwargs.pop('config', {})
        ValidatedBusDriver.__init__(self, *args, **kwargs)

        self.config = AvalonSTPkts._default_config.copy()

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

        self.use_empty = (num_data_symbols > 1)
        self.config["useEmpty"] = self.use_empty

        word = BinaryValue(n_bits=len(self.bus.data),
                           bigEndian=self.config["firstSymbolInHighOrderBits"])

        single = BinaryValue(n_bits=1, bigEndian=False)

        word.binstr   = "x" * len(self.bus.data)
        single.binstr = "x"

        self.bus.valid <= 0
        self.bus.data <= word
        self.bus.startofpacket <= single
        self.bus.endofpacket <= single

        if self.use_empty:
            empty = BinaryValue(n_bits=len(self.bus.empty), bigEndian=False,
                                value="x" * len(self.bus.empty))
            self.bus.empty <= empty

        if hasattr(self.bus, 'channel'):
            if len(self.bus.channel) > 128:
                raise AttributeError("Avalon-ST interface specification defines channel width as 1-128. "
                                     "%d channel width is %d" % (self.name, len(self.bus.channel)))
            maxChannel = (2 ** len(self.bus.channel)) -1
            if self.config['maxChannel'] > maxChannel:
                raise AttributeError("%s has maxChannel=%d, but can only support a maximum channel of "
                                     "(2**channel_width)-1=%d, channel_width=%d" %
                                     (self.name, self.config['maxChannel'], maxChannel, len(self.bus.channel)))
            channel = BinaryValue(n_bits=len(self.bus.channel), bigEndian=False,
                                  value="x" * len(self.bus.channel))
            self.bus.channel <= channel

    @coroutine
    def _wait_ready(self):
        """Wait for a ready cycle on the bus before continuing.

            Can no longer drive values this cycle...

            FIXME assumes readyLatency of 0
        """
        yield ReadOnly()
        while not self.bus.ready.value:
            yield RisingEdge(self.clock)
            yield ReadOnly()

    @coroutine
    def _send_string(self, string, sync=True, channel=None):
        """Args:
            string (str): A string of bytes to send over the bus.
            channel (int): Channel to send the data on.
        """
        # Avoid spurious object creation by recycling
        clkedge = RisingEdge(self.clock)
        firstword = True

        # FIXME busses that aren't integer numbers of bytes
        bus_width = int(len(self.bus.data) / 8)

        word = BinaryValue(n_bits=len(self.bus.data),
                           bigEndian=self.config["firstSymbolInHighOrderBits"])

        single = BinaryValue(n_bits=1, bigEndian=False)
        if self.use_empty:
            empty = BinaryValue(n_bits=len(self.bus.empty), bigEndian=False)

        # Drive some defaults since we don't know what state we're in
        if self.use_empty:
            self.bus.empty <= 0
        self.bus.startofpacket <= 0
        self.bus.endofpacket <= 0
        self.bus.valid <= 0
        if hasattr(self.bus, 'error'):
            self.bus.error <= 0

        if hasattr(self.bus, 'channel'):
            self.bus.channel <= 0
        elif channel is not None:
            raise TestError("%s does not have a channel signal" % self.name)

        while string:
            if not firstword or (firstword and sync):
                yield clkedge

            # Insert a gap where valid is low
            if not self.on:
                self.bus.valid <= 0
                for _ in range(self.off):
                    yield clkedge

                # Grab the next set of on/off values
                self._next_valids()

            # Consume a valid cycle
            if self.on is not True and self.on:
                self.on -= 1

            self.bus.valid <= 1
            if hasattr(self.bus, 'channel'):
                if channel is None:
                    self.bus.channel <= 0
                elif channel > self.config['maxChannel'] or channel < 0:
                    raise TestError("%s: Channel value %d is outside range 0-%d" %
                                    (self.name, channel, self.config['maxChannel']))
                else:
                    self.bus.channel <= channel

            if firstword:
                self.bus.startofpacket <= 1
                firstword = False
            else:
                self.bus.startofpacket <= 0

            nbytes = min(len(string), bus_width)
            data = string[:nbytes]
            word.buff = data

            if len(string) <= bus_width:
                self.bus.endofpacket <= 1
                if self.use_empty:
                    self.bus.empty <= bus_width - len(string)
                string = ""
            else:
                string = string[bus_width:]

            self.bus.data <= word

            # If this is a bus with a ready signal, wait for this word to
            # be acknowledged
            if hasattr(self.bus, "ready"):
                yield self._wait_ready()

        yield clkedge
        self.bus.valid <= 0
        self.bus.endofpacket <= 0
        word.binstr   = "x" * len(self.bus.data)
        single.binstr = "x"
        self.bus.data <= word
        self.bus.startofpacket <= single
        self.bus.endofpacket <= single

        if self.use_empty:
            empty.binstr = "x" * len(self.bus.empty)
            self.bus.empty <= empty
        if hasattr(self.bus, 'channel'):
            channel_value = BinaryValue(n_bits=len(self.bus.channel), bigEndian=False,
                                        value="x" * len(self.bus.channel))
            self.bus.channel <= channel_value

    @coroutine
    def _send_iterable(self, pkt, sync=True):
        """Args:
            pkt (iterable): Will yield objects with attributes matching the
                signal names for each individual bus cycle.
        """
        clkedge = RisingEdge(self.clock)
        firstword = True

        for word in pkt:
            if not firstword or (firstword and sync):
                yield clkedge

            firstword = False

            # Insert a gap where valid is low
            if not self.on:
                self.bus.valid <= 0
                for _ in range(self.off):
                    yield clkedge

                # Grab the next set of on/off values
                self._next_valids()

            # Consume a valid cycle
            if self.on is not True and self.on:
                self.on -= 1

            if not hasattr(word, "valid"):
                self.bus.valid <= 1
            else:
                self.bus <= word

            # Wait for valid words to be acknowledged
            if not hasattr(word, "valid") or word.valid:
                if hasattr(self.bus, "ready"):
                    yield self._wait_ready()

        yield clkedge
        self.bus.valid <= 0

    @coroutine
    def _driver_send(self, pkt, sync=True, channel=None):
        """Send a packet over the bus.

        Args:
            pkt (str or iterable): Packet to drive onto the bus.
            channel (None or int): Channel attributed to the packet.

        If ``pkt`` is a string, we simply send it word by word

        If ``pkt`` is an iterable, it's assumed to yield objects with
        attributes matching the signal names.
        """

        # Avoid spurious object creation by recycling
        if isinstance(pkt, str):
            self.log.debug("Sending packet of length %d bytes", len(pkt))
            self.log.debug(hexdump(pkt))
            yield self._send_string(pkt, sync=sync, channel=channel)
            self.log.debug("Successfully sent packet of length %d bytes", len(pkt))
        else:
            if channel is not None:
                self.log.warning("%s is ignoring channel=%d because pkt is an iterable", self.name, channel)
            yield self._send_iterable(pkt, sync=sync)
