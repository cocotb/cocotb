#!/usr/bin/env python
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

import cocotb
from scapy.all import *

class Feed(object):
    def __init__(self, name, filepath=None):
        self.name = name
        self._packets = {}
        self._filepath = filepath
        self.fullname = '\'' + self.name + '\''
        self.log = logging.getLogger('cocotb.' + self.name)
        if self._filepath:
            self._source = open(self._filepath)
            self.log.debug("loaded file %s" % self._filepath)
        self.log.debug("Created feed!")

    def addmsg(self, tag, data):
        """ Add a defined message to the internal feed store """
        self._packets[tag] = data

    def getmsg(self):
        """ Get a string representation of the current list head
            This packet will be ready to send
        """
        if self._packets:
            tag, packet = self._packets.popitem()
            return str(packet)
        else:
            self.log.warn("No packets in feed %s" % self.fullname)
            return None

