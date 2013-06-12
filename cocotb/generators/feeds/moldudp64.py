#! /usr/bin/env python
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

# Set log level to benefit from Scapy warnings
import logging
logging.getLogger("scapy").setLevel(1)

from scapy.all import *
from packet_util import *

class MsgDataLen(FieldLenField):
    def __init__(self, name, default, fld):
        FieldLenField.__init__(self, name, default)
        self.fld = fld

    def i2len(self, pkt, x):
        return len(self.i2len(pkt, x))

    def i2m(self, pkt, x):
        if x is None:
            f = pkt.get_field(self.fld)
            x = f.i2len(pkt, pkt.getfieldval(self.fld))
        return int_to_packed(x, 16, 8)

    def m2i(self, pkt, x):
        if x is None:
            return None, 0
        return x[0:2]

    def getfield(self, pkt, s):
        i = len(s) - 1
        return s[i:], self.m2i(pkt, s[:i])

    def addfield(self, pkt, s, val):
        return s+self.i2m(pkt, val)

class MoldCountField(FieldLenField):
    def __init__(self, name, length, count):
        FieldLenField.__init__(self, name, None, count_of=count)
        self.length = length

    def i2m(self, pkt, x):
        fld,fval = pkt.getfield_and_val(self.count_of)
        f = fld.i2count(pkt, fval)
        return int_to_packed(f, self.length * 8, 8)

    def addfield(self, pkt, s, val):
        return s+self.i2m(pkt, val)


class MessageBlock(Packet):
    fields_desc = [ MsgDataLen("length", None, "data"),
                    StrLenField("data", "", length_from="length") ]


class Moldudp64(Packet):
    name = "Moldudp64"
    fields_desc = [ LongDecimalField("session", 0, 10),
                    LongDecimalField("seqnum", 0, 8),
                    MoldCountField("msgcnt", 2, "msgblock"),
                    PacketListField("msgblock", [], MessageBlock) ]

    def insertblock(self, payload):
        self.msgblock.append(MessageBlock(data=payload))
