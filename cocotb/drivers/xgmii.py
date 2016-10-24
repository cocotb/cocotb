''' Copyright (c) 2013 Potential Ventures Ltd
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd nor the names of its
      contributors may be used to endorse or promote products derived from this
      software without specific prior written permission.

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
Drivers for XGMII
"""

import struct
import zlib

import cocotb
from cocotb.triggers import RisingEdge
from cocotb.drivers import Driver
from cocotb.utils import hexdump
from cocotb.binary import BinaryValue

_XGMII_IDLE      = "\x07"  # noqa
_XGMII_START     = "\xFB"  # noqa
_XGMII_TERMINATE = "\xFD"  # noqa

# Preamble is technically supposed to be 7 bytes of 0x55 but it seems that it's
# permissible for the start byte to replace one of the preamble bytes
# see http://grouper.ieee.org/groups/802/3/10G_study/email/msg04647.html
_PREAMBLE_SFD = "\x55\x55\x55\x55\x55\x55\xD5"


class _XGMIIBus(object):
    """
    Helper object for abstracting the underlying bus format

    Index bytes directly on this object, pass a tuple of (value, ctrl) to
    set a byte.

    For example:

    >>> xgmii = _XGMIIBus(4)
    >>> xgmii[0] = (_XGMII_IDLE, True) # Control byte
    >>> xgmii[1] = ("\x55", False)     # Data byte
    """

    def __init__(self, nbytes, interleaved=True):
        """
        Args:
            nbytes (int):       The number of bytes transferred per clock cycle
                                (usually 8 for SDR, 4 for DDR)

        Kwargs:
            interleaved (bool): The arrangement of control bits on the bus.

                                If interleaved we have a bus with 9-bits per
                                byte, the control bit being the 9th bit of each
                                byte.

                                If not interleaved then we have a byte per data
                                byte plus a control bit per byte in the MSBs.
        """

        self._value = BinaryValue(bits=nbytes*9, bigEndian=False)
        self._integer = long(0)
        self._interleaved = interleaved
        self._nbytes = nbytes

        # Default to idle
        for i in range(nbytes):
            self[i] = (0x07, True)

    def __setitem__(self, index, value):
        byte, ctrl = value

        if isinstance(byte, str):
            byte = ord(byte)

        if index >= self._nbytes:
            raise IndexError("Attempt to access byte %d of a %d byte bus" % (
                index, self._nbytes))

        if self._interleaved:
            self._integer |= (byte << (index * 9))
            self._integer |= (int(ctrl) << (9*index + 8))
        else:
            self._integer |= (byte << (index * 8))
            self._integer |= (int(ctrl) << (self._nbytes*8 + index))

        self._value.integer = self._integer

    @property
    def value(self):
        """
        Get the integer representation of this data word suitable for driving
        onto the bus.

        NB clears the value
        """
        self._value.integer = self._integer
        self._integer = long(0)
        return self._value

    def __len__(self):
        return self._nbytes


class XGMII(Driver):
    """
    XGMII driver
    """

    def __init__(self, signal, clock, interleaved=True):
        """
        Args:
            signal (SimHandle):         The xgmii data bus

            clock (SimHandle):          The associated clock (assumed to be
                                        driven by another coroutine)

        Kwargs:
            interleaved (bool:          Whether control bits are interleaved
                                        with the data bytes or not.

        If interleaved the bus is
            byte0, byte0_control, byte1, byte1_control ....

            Otherwise expect:

            byte0, byte1, ..., byte0_control, byte1_control...
        """
        self.log = signal._log
        self.signal = signal
        self.clock = clock
        self.bus = _XGMIIBus(len(signal)/9, interleaved=interleaved)
        Driver.__init__(self)

    @staticmethod
    def layer1(packet):
        """Take an Ethernet packet (as a string) and format as a layer 1 packet

           Pads to 64-bytes,
           prepends preamble and appends 4-byte CRC on the end
        """
        if len(packet) < 60:
            padding = "\x00" * (60 - len(packet))
            packet += padding
        return (_PREAMBLE_SFD + packet +
                struct.pack("<I", zlib.crc32(packet) & 0xFFFFFFFF))

    def idle(self):
        """Helper to set bus to IDLE state"""
        for i in range(len(self.bus)):
            self.bus[i] = (_XGMII_IDLE, True)
        self.signal <= self.bus.value

    def terminate(self, index):
        """Helper function to terminate from a provided lane index"""
        self.bus[index] = (_XGMII_TERMINATE, True)

        if index < len(self.bus) - 1:

            for rem in range(index + 1, len(self.bus)):
                self.bus[rem] = (_XGMII_IDLE, True)

    @cocotb.coroutine
    def _driver_send(self, pkt, sync=True):
        """Send a packet over the bus

        Args:
            pkt (str): Ethernet packet to drive onto the bus
        """
        pkt = self.layer1(str(pkt))

        self.log.debug("Sending packet of length %d bytes" % len(pkt))
        self.log.debug(hexdump(pkt))

        clkedge = RisingEdge(self.clock)
        if sync:
            yield clkedge

        self.bus[0] = (_XGMII_START, True)

        for i in range(1, len(self.bus)):
            self.bus[i] = (pkt[i-1], False)

        pkt = pkt[len(self.bus)-1:]
        self.signal <= self.bus.value
        yield clkedge

        done = False

        while pkt:

            for i in range(len(self.bus)):
                if i == len(pkt):
                    self.terminate(i)
                    pkt = ""
                    done = True
                    break
                self.bus[i] = (pkt[i], False)

            self.signal <= self.bus.value
            yield clkedge
            pkt = pkt[len(self.bus):]

        if not done:
            self.terminate(0)
            self.signal <= self.bus.value
            yield clkedge

        self.idle()
        yield clkedge
        self.log.debug("Successfully sent packet")
