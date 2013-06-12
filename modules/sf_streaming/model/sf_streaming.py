''' Copyright (c) 2013 Potential Ventures Ltd
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd nor the
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
    All things sf_streaming bus related go here
"""

from ctypes import *
from scapy.all import *

# The only thing we export is the SFStreamingPacket
__all__ = ["SFStreamingPacket", "SFStreamingBusWord"]

# Helper functions FIXME move somewhere common
def pack(ctypes_obj):
    """Convert a ctypes structure into a python string"""
    return string_at(addressof(ctypes_obj), sizeof(ctypes_obj))


def unpack(ctypes_obj, string, bytes=None):
    """Unpack a python string into a ctypes structure

    If the length of the string is not the correct size for the memory footprint of the
    ctypes structure then the bytes keyword argument must be used
    """
    if bytes is None and len(string) != sizeof(ctypes_obj):
        raise ValueError("Attempt to unpack a string of size %d into a struct of size %d" % (len(string), sizeof(ctypes_obj)))
    if bytes is None: bytes = len(string)
    memmove(addressof(ctypes_obj), string, bytes)


# Enumerations for the detected protocol
SF_PKT_PROTO_RAW = 0
SF_PKT_PROTO_TCP = 1
SF_PKT_PROTO_UDP = 2
SF_PKT_PROTO_IP_UNKNOWN = 3

class SFPktDesc(Structure):
    """Descriptor containing the information about the payload of the packet.

        see sf_streaming_pkg.sv for full details
        """
    _fields_ = [
        ("protocol",            c_uint8, 2),
        ("payload_offset",      c_uint8, 6)]

class SFMetaWord(Structure):
    """First word prepended to each packet"""
    _pack_ = 1
    _fields_ = [
        ("timestamp",           c_uint32),
        ("descriptor",          SFPktDesc),
        ("lookup_context",      c_uint16),
        ("scratch",             c_uint8)]


class SFStreamingData(Structure):
    _pack_ = 1
    _fields_ = [
        ("data",                c_uint64),
        ("ecc",                 c_uint8)]

class SFStreamingBusWord(Structure):
    _pack_ = 1
    _fields_ = [
        ("data",                SFStreamingData),
        ("empty",               c_uint8,        3),
        ("startofpacket",       c_uint8,        1),
        ("endofpacket",         c_uint8,        1),
        ("error",               c_uint8,        2),
        ("channel",             c_uint8,        1)]

    def __str__(self):
        return "sop: %d\teop: %d\tchannel: %d\tempty: %d\tdata: %016x" % (self.startofpacket, self.endofpacket, self.channel, self.empty, self.data.data)

class SFStreamingPacket(object):
    """Useful container class to make using the sf_streaming bus more convenient

    TODO:
        Don't currently handle metawords in the middle of the packet.

        Probably want to make the underlying data structure an array of SFStreamingBusWord.

        We could then alias self.pkt to pull out the packet contents from the array.
    """

    def __init__(self, pkt):
        """pkt is a string"""
        self.metaword = SFMetaWord()
        self.pkt = pkt
        self.parse()
        self._ptr = 0

    def parse(self):
        """Parse the packet and populate the metaword descriptor field

            FIXME: need to handle GRE here
        """
        p = Ether(self.pkt)

        if p.payload.name != 'IP':
            self.metaword.descriptor.protocol           = SF_PKT_PROTO_RAW
            self.metaword.descriptor.payload_offset     = self.pkt.find(str(p.payload))
            return

        ip = p.payload

        if ip.payload.name == "UDP":
            self.metaword.descriptor.protocol           = SF_PKT_PROTO_UDP
            self.metaword.descriptor.payload_offset     = self.pkt.find(str(ip.payload.payload))
            return

        # For TCP we only point to the start of the IP payload since we don't
        # currently parse out the TCP header
        if ip.payload.name == "TCP":
            self.metaword.descriptor.protocol           = SF_PKT_PROTO_TCP
        else:
            self.metaword.descriptor.protocol           = SF_PKT_PROTO_IP_UNKNOWN

        self.metaword.descriptor.payload_offset     = self.pkt.find(str(ip.payload))
        return

    def __len__(self):
        return len(self.pkt) + 8

    def __iter__(self):
        self._ptr = None
        return self

    @property
    def payload(self):
        """Returns the payload of the packet as defined by the descriptor field"""
        return str(self.pkt)[self.metaword.descriptor.payload_offset * 4 + 14:]

    def next(self):
        if self._ptr >= len(self.pkt): raise StopIteration

        word = SFStreamingBusWord()
        data = c_uint64()

        # Metaword first on channel 1
        if self._ptr is None:
            unpack(data, pack(self.metaword))
            word.data.data = data
            word.empty = 0
            word.startofpacket = 1
            word.endofpacket = 0
            word.channel = 1
            word.error = 0
            self._ptr = 8
            return word

        # Into the packet data
        if self._ptr + 8 > len(self.pkt):
            chunk = self.pkt[self._ptr:]
        else:
            chunk = self.pkt[self._ptr:self._ptr + 8]
        unpack(data, chunk, bytes=len(chunk))
        word.data.data = data
        word.empty = 8 - len(chunk)
        word.channel = 0
        word.error = 0
        word.startofpacket = 0
        word.endofpacket = 0
        self._ptr += 8
        if self._ptr >= len(self.pkt):
            word.endofpacket = 1
        return word


def test_stuff():
    pkt = Ether() / IP() / UDP() / "Here is some payload"

    wrapped_pkt = SFStreamingPacket(str(pkt))

    for word in wrapped_pkt:
        print str(word)

if __name__ == "__main__":
    test_stuff()
