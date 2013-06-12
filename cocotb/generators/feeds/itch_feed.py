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
import cocotb
from scapy.all import *
from cocotb.generators.feeds import Feed
from cocotb.generators.feeds.moldudp64 import Moldudp64

""" Todo
    Specify max number of blocks per underlying mold
"""

class ItchFeed(Feed):
    """ Class to represent a steam of Itch4.0 messages """

    def __init__(self, name="default_itch", session=0, seqnum=0):
        """ Session is the session for the current stream
            Seqnum is the starting sequence number
        """
        Feed.__init__(self, name, None)
        self._session = session;
        self._seqnum = seqnum

    def addmsg(self, msg):
        """ Add a mold64 encapsulated msg to the queue """
        packet = Ether()/IP()/UDP()/Moldudp64(session=self._session, seqnum=self._seqnum, msgblock=[])
        mold = packet.getlayer(Moldudp64)
        mold.insertblock(msg)
        ret = self._seqnum
        self._seqnum += 1
        super(self.__class__, self).addmsg(ret, packet)
        return ret

    def appendmsg(self, seqnum, msg):
        """ Append another msg to the specified sequence number """

    def getmsg(self):
        return Feed.getmsg(self)

if __name__ == "__main__":
    interact(mydict=globals(), mybanner="ITCH 4.0 packet generator")
