''' Copyright (c) 2014 Potential Ventures Ltd
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd,
      SolarFlare Communications Inc nor the
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
Drivers for Advanced Microcontroller Bus Architecture
"""
import cocotb
from cocotb.triggers import RisingEdge, ReadOnly, Lock
from cocotb.drivers import BusDriver
from cocotb.result import ReturnValue
from cocotb.binary import BinaryValue

import binascii
import array
import struct
import pydevd

class AXIReadError(Exception): pass

class AXI4LiteMaster(BusDriver):
    """
    AXI4-Lite Master

    TODO: Kill all pending transactions if reset is asserted...
    """
    _signals = ["AWVALID", "AWADDR", "AWREADY",         # Write address channel
                "WVALID", "WREADY", "WDATA", "WSTRB",   # Write data channel
                "BVALID", "BREADY", "BRESP",            # Write response channel
                "ARVALID", "ARADDR", "ARREADY",         # Read address channel
                "RVALID", "RREADY", "RRESP", "RDATA"]   # Read data channel

    def __init__(self, entity, name, clock):
        BusDriver.__init__(self, entity, name, clock)

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
        Send the write address, with optional delay
        """
        yield self.write_address_busy.acquire()
        for cycle in xrange(delay):
            yield RisingEdge(self.clock)

        self.bus.AWADDR         <= address
        self.bus.AWVALID        <= 1

        while True:
            yield ReadOnly()
            if self.bus.AWREADY.value:
                break
            yield RisingEdge(self.clock)
        yield RisingEdge(self.clock)
        self.bus.AWVALID        <= 0
        self.write_address_busy.release()

    @cocotb.coroutine
    def _send_write_data(self, data, delay=0, byte_enable=0xF):
        """
        Send the write address, with optional delay
        """
        yield self.write_data_busy.acquire()
        for cycle in xrange(delay):
            yield RisingEdge(self.clock)

        self.bus.WDATA          <= data
        self.bus.WVALID         <= 1
        self.bus.WSTRB          <= byte_enable

        while True:
            yield ReadOnly()
            if self.bus.WREADY.value:
                break
            yield RisingEdge(self.clock)
        yield RisingEdge(self.clock)
        self.bus.WVALID        <= 0
        self.write_data_busy.release()


    @cocotb.coroutine
    def write(self, address, value, byte_enable=0xf, address_latency=0, data_latency=0):
        """
        Write a value to an address.

        The *_latency KWargs allow control over the delta 
        """
        

        c_addr = cocotb.fork(self._send_write_address(address, delay=address_latency))
        c_data = cocotb.fork(self._send_write_data(value, byte_enable=byte_enable, delay=data_latency))



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
            raise AXIReadError("Write to address 0x%08x failed with BRESP: %d" %(
                address, int(result)))

        raise ReturnValue(result)


    @cocotb.coroutine
    def read(self, address, sync=True):
        """
        Read from an address.
        """
        if sync:
            yield RisingEdge(self.clock)

        self.bus.ARADDR         <= address
        self.bus.ARVALID        <= 1

        while True:
            yield ReadOnly()
            if self.bus.ARREADY.value:
                break
            yield RisingEdge(self.clock)

        yield RisingEdge(self.clock)
        self.bus.ARVALID        <= 0

        while True:
            yield ReadOnly()
            if self.bus.RVALID.value and self.bus.RREADY.value:
                data = self.bus.RDATA.value
                result = self.bus.RRESP.value
                break
            yield RisingEdge(self.clock)

        if int(result):
            raise AXIReadError("Read address 0x%08x failed with RRESP: %d" %(
                address, int(result)))

        raise ReturnValue(data)



class AXI4Slave(BusDriver):
    '''
    AXI4 Slave
    
    Monitors an internal memory and handles read and write requests.
    '''
    _signals = [
    "ACLK"             , #    input                 

    "ARREADY"          , #    input                 
    "ARVALID"          , #    output                
    "ARADDR"           , #    output      [31 : 0]  
                      
    "ARLEN"            , #    output      [3 : 0]   
    "ARSIZE"           , #    output      [2 : 0]   
    "ARBURST"          , #    output      [1 : 0]   
    "ARPROT"           , #    output      [2 : 0]   
                      
    "RREADY"           , #    output                
    "RVALID"           , #    input                 
    "RDATA"            , #    input       [63 : 0]  
    "RLAST"            , #    input                 
                      
    "AWREADY"          , #    input     
    "AWADDR"           , #    output      [31 : 0]  
    "AWVALID"          , #    output 
    "AWLEN"            , #    output      [3 : 0]  
    "AWPROT"           , #    output      [2 : 0]   
    "AWSIZE"           , #    output      [2 : 0]   
    "AWBURST"          , #    output      [1 : 0] 
    
    "WREADY"           , #    input      
    "WLAST"            , #    output   
    "WVALID"           , #    output  
    "WDATA"            , #    output      [63 : 0]  
    "WSTRB"            , #    output      [7 : 0]   
    
    "BVALID"           , #    input                 
    "BREADY"           , #    output                
    "BRESP"            , #    input       [1 : 0]   

    "RRESP"            , #    input       [1 : 0]   

    "RCOUNT"           , #    input       [7 : 0]   
    "WCOUNT"           , #    input       [7 : 0]   
    "RACOUNT"          , #    input       [2 : 0]   
    "WACOUNT"          , #    input       [5 : 0]   

    "RDISSUECAP1_EN"   , #    output                
    "WRISSUECAP1_EN"   , #    output                
    "ARLOCK"           , #    output      [1 : 0]   
    "AWLOCK"           , #    output      [1 : 0]   
    "ARCACHE"          , #    output      [3 : 0]   
    "AWCACHE"          , #    output      [3 : 0]   
    "ARQOS"            , #    output      [3 : 0]  
    "AWQOS"            , #    output      [3 : 0]   
    "ARID"             , #    output      [5 : 0]   
    "AWID"             , #    output      [5 : 0]   
    "BID"              , #    input       [5 : 0]   
    "RID"              , #    input       [5 : 0]   
    "WID"              , #    output      [5 : 0]   
    ]

    def __init__(self, entity, name, clock, memory, reset=None, reset_n=None, callback=None, event=None, big_endian=False, print_debug=False):
        '''
        Constructor
        '''
        BusDriver.__init__(self,entity,name,clock)
        self.clock = clock
        
        self.big_endain = big_endian
        self.bus.ARREADY.setimmediatevalue(1)
        self.bus.RVALID.setimmediatevalue(0)
        self.bus.RLAST.setimmediatevalue(0)
        self.bus.AWREADY.setimmediatevalue(1)
        
        self._memory = memory
        self.print_debug = print_debug
        
#         self._memory = array.array('B',((i % 256) for i in range(MEMORY_SIZE_IN_BYTES)))
        
        self.write_address_busy = Lock("%s_wabusy" % name)
        self.read_address_busy = Lock("%s_rabusy" % name)
        self.write_data_busy = Lock("%s_wbusy" % name)
        
        cocotb.fork(self._read_data())
        cocotb.fork(self._write_data())
    
    def _size_to_bytes_in_beat(self,AxSIZE):
        bytes_in_transfer = 0
        if AxSIZE == 0:
            bytes_in_transfer = 1
        elif AxSIZE == 1:
            bytes_in_transfer = 2
        elif AxSIZE == 2:
            bytes_in_transfer = 4
        elif AxSIZE == 3:
            bytes_in_transfer = 8
        elif AxSIZE == 4:
            bytes_in_transfer = 16
        elif AxSIZE == 5:
            bytes_in_transfer = 32
        elif AxSIZE == 6:
            bytes_in_transfer = 64
        elif AxSIZE == 7:
            bytes_in_transfer = 128
        else:
            bytes_in_transfer = None
            
        return bytes_in_transfer

    @cocotb.coroutine
    def _write_data(self):
        clock_re = RisingEdge(self.clock)

        while True:
            while True:
                self.bus.WREADY <= 0
                yield ReadOnly()
                if self.bus.AWVALID.value:
                    self.bus.WREADY <= 1
                    break
                yield clock_re
                
            
            yield ReadOnly()
            _awaddr  = self.bus.AWADDR.value
            _awlen   = self.bus.AWLEN.value
            _awsize  = self.bus.AWSIZE.value
            _awburst = self.bus.AWBURST.value
            _awprot  = self.bus.AWPROT.value
            
            burst_length = _awlen + 1
            bytes_in_beat = self._size_to_bytes_in_beat(_awsize)
            
            word = BinaryValue(bits=bytes_in_beat*8, bigEndian=self.big_endain)
            
            if self.print_debug:
                print "AWADDR  %d" % _awaddr 
                print "AWLEN   %d" % _awlen  
                print "AWSIZE  %d" % _awsize 
                print "AWBURST %d" % _awburst
                print "BURST_LENGTH %d" % burst_length
                print "Bytes in beat %d" % bytes_in_beat
            
            burst_count = burst_length


            yield clock_re
            
            if bytes_in_beat != 8:
                print "Hmm bytes_in_beat not 8?"
            
            while True:
                if self.bus.WVALID.value:
                    word = self.bus.WDATA.value
                    word.big_endian = self.big_endain
                    if self.print_debug:
                        print binascii.hexlify(word.get_buff()) + " to " + str(_awaddr+((burst_length-burst_count)*bytes_in_beat)) + " : " + str(_awaddr+(((burst_length-burst_count)+1)*bytes_in_beat))
                    self._memory[_awaddr+((burst_length-burst_count)*bytes_in_beat):_awaddr+(((burst_length-burst_count)+1)*bytes_in_beat)] = array.array('B',word.get_buff())
                    burst_count -= 1
                    if burst_count == 0:
                        break
                yield clock_re
      

    @cocotb.coroutine
    def _read_data(self):
        clock_re = RisingEdge(self.clock)

        while True:
            while True:
                yield ReadOnly()
                if self.bus.ARVALID.value:
                    break
                yield clock_re
            
            yield ReadOnly()
            _araddr  = self.bus.ARADDR.value
            _arlen   = self.bus.ARLEN.value
            _arsize  = self.bus.ARSIZE.value
            _arburst = self.bus.ARBURST.value
            _arprot  = self.bus.ARPROT.value
            
            burst_length = _arlen + 1
            bytes_in_beat = self._size_to_bytes_in_beat(_arsize)
            
            word = BinaryValue(bits=bytes_in_beat*8, bigEndian=self.big_endain)
            
            if self.print_debug:
                print "ARADDR  %d" % _araddr 
                print "ARLEN   %d" % _arlen  
                print "ARSIZE  %d" % _arsize 
                print "ARBURST %d" % _arburst
                print "BURST_LENGTH %d" % burst_length
                print "Bytes in beat %d" % bytes_in_beat
            
            burst_count = burst_length
            

            yield clock_re
            
            if bytes_in_beat != 8:
                print "Hmm bytes_in_beat not 8?"
            
            while True:
                self.bus.RVALID <= 1
                yield ReadOnly()
                if self.bus.RREADY.value:
                    word.buff = self._memory[_araddr+((burst_length-burst_count)*bytes_in_beat):_araddr+(((burst_length-burst_count)+1)*bytes_in_beat)].tostring()
                    if self.print_debug:
                        print binascii.hexlify(self._memory[_araddr+((burst_length-burst_count)*bytes_in_beat):_araddr+(((burst_length-burst_count)+1)*bytes_in_beat)])
                    self.bus.RDATA  <= word
                    if burst_count == 1:
                        self.bus.RLAST <= 1
                yield clock_re
                burst_count -= 1
                self.bus.RLAST <= 0
                if burst_count == 0:
                    break

