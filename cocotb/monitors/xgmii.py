# Copyright (c) 2013 Potential Ventures Ltd
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd nor the names of its
#       contributors may be used to endorse or promote products derived from this
#       software without specific prior written permission.
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

"""Monitor for XGMII (10 Gigabit Media Independent Interface)."""

# By default cast to scapy packets, otherwise we pass the string of bytes
try:
    from scapy.all import Ether
    _have_scapy = True
except ImportError:
    _have_scapy = False

import struct
import zlib

import cocotb
from cocotb.utils import hexdump
from cocotb.monitors import Monitor
from cocotb.triggers import RisingEdge

_XGMII_IDLE      = "\x07"  # noqa
_XGMII_START     = "\xFB"  # noqa
_XGMII_TERMINATE = "\xFD"  # noqa

_PREAMBLE_SFD = "\x55\x55\x55\x55\x55\x55\xD5"


class XGMII(Monitor):
    """XGMII (10 Gigabit Media Independent Interface) Monitor.

    Assumes a single vector, either 4 or 8 bytes plus control bit for each byte.

    If interleaved is ``True`` then the control bits are adjacent to the bytes.
    """

    def __init__(self, signal, clock, interleaved=True, callback=None,
                 event=None):
        """Args:
            signal (SimHandle): The XGMII data bus.
            clock (SimHandle): The associated clock (assumed to be
                driven by another coroutine).
            interleaved (bool, optional): Whether control bits are interleaved
                with the data bytes or not.

        If interleaved the bus is
            byte0, byte0_control, byte1, byte1_control, ...

        Otherwise expect
            byte0, byte1, ..., byte0_control, byte1_control, ...
        """
        self.log = signal._log
        self.clock = clock
        self.signal = signal
        self.bytes = len(self.signal) // 9
        self.interleaved = interleaved
        Monitor.__init__(self, callback=callback, event=event)

    def _get_bytes(self):
        """Take a value and extract the individual bytes and control bits.

        Returns a tuple of lists.
        """
        value = self.signal.value.integer
        bytes = []
        ctrls = []
        byte_shift = 8
        ctrl_base = 8 * self.bytes
        ctrl_inc = 1
        if self.interleaved:
            byte_shift += 1
            ctrl_base = 8
            ctrl_inc = 9

        for i in range(self.bytes):
            bytes.append(chr((value >> (i * byte_shift)) & 0xff))
            ctrls.append(bool(value & (1 << ctrl_base)))
            ctrl_base += ctrl_inc

        return ctrls, bytes

    def _add_payload(self, ctrl, bytes):
        """Take the payload and return true if more to come"""
        for index, byte in enumerate(bytes):
            if ctrl[index]:
                if byte != _XGMII_TERMINATE:
                    self.log.error("Got control character in XGMII payload")
                    self.log.info("data = :" +
                                  " ".join(["%02X" % ord(b) for b in bytes]))
                    self.log.info("ctrl = :" +
                                  " ".join(["%s" % str(c) for c in ctrl]))
                    self._pkt = ""
                return False

            self._pkt += byte
        return True

    @cocotb.coroutine
    def _monitor_recv(self):
        clk = RisingEdge(self.clock)
        self._pkt = ""

        while True:
            yield clk
            ctrl, bytes = self._get_bytes()

            if ctrl[0] and bytes[0] == _XGMII_START:

                ctrl, bytes = ctrl[1:], bytes[1:]

                while self._add_payload(ctrl, bytes):
                    yield clk
                    ctrl, bytes = self._get_bytes()

            if self._pkt:

                self.log.debug("Received:\n%s" % (hexdump(self._pkt)))

                if len(self._pkt) < 64 + 7:
                    self.log.error("Received a runt frame!")
                if len(self._pkt) < 12:
                    self.log.error("No data to extract")
                    self._pkt = ""
                    continue

                preamble_sfd = self._pkt[0:7]
                crc32 = self._pkt[-4:]
                payload = self._pkt[7:-4]

                if preamble_sfd != _PREAMBLE_SFD:
                    self.log.error("Got a frame with unknown preamble/SFD")
                    self.log.error(hexdump(preamble_sfd))
                    self._pkt = ""
                    continue

                expected_crc = struct.pack("<I",
                                           (zlib.crc32(payload) & 0xFFFFFFFF))

                if crc32 != expected_crc:
                    self.log.error("Incorrect CRC on received packet")
                    self.log.info("Expected: %s" % (hexdump(expected_crc)))
                    self.log.info("Received: %s" % (hexdump(crc32)))

                # Use scapy to decode the packet
                if _have_scapy:
                    p = Ether(payload)
                    self.log.debug("Received decoded packet:\n%s" % p.show2())
                else:
                    p = payload

                self._recv(p)
                self._pkt = ""
