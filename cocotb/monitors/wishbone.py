
import cocotb
from cocotb.decorators import coroutine
from cocotb.monitors import BusMonitor
from cocotb.triggers import RisingEdge
from cocotb.result import TestFailure
from cocotb.decorators import public  
import Queue


class WBAux():
    """Wishbone Auxiliary Wrapper Class, wrap meta informations on bus transaction (internal only)
    """
    adr   = 0
    datwr = None     
    sel         = 0xf
    waitStall   = 0
    waitIdle    = 0
    ts          = 0
    
    def __init__(self, sel, adr, datwr, waitStall, waitIdle, tsStb):
        self.adr        = adr
        self.datwr      = datwr        
        self.sel        = sel
        self.waitStall  = waitStall
        self.ts         = tsStb
        self.waitIdle   = waitIdle

@public
class WBRes():
    """Wishbone Result Wrapper Class. What's happend on the bus plus meta information on timing
    """
    adr   = 0
    sel   = 0xf
    datwr = None    
    datrd = None
    ack = False
    waitstall = 0
    waitack = 0
    waitidle = 0
    
    def __init__(self, ack, sel, adr, datrd, datwr, waitIdle, waitStall, waitAck):
        self.ack        = ack
        self.sel        = sel
        self.adr        = adr
        self.datrd      = datrd
        self.datwr      = datwr
        self.waitStall  = waitStall
        self.waitAck    = waitAck
        self.waitIdle   = waitIdle
          

class Wishbone(BusMonitor):
    """Wishbone
    """
    _width = 32
    
    _signals = ["cyc", "stb", "we", "sel", "adr", "datwr", "datrd", "ack"]
    _optional_signals = ["err", "stall", "rty"]
    replyTypes = {1 : "ack", 2 : "err", 3 : "rty"}  

    def __init__(self, *args, **kwargs):
        self._width = kwargs.pop('width', 32)
        BusMonitor.__init__(self, *args, **kwargs)
        # Drive some sensible defaults (setimmediatevalue to avoid x asserts)
        self.bus.ack.setimmediatevalue(0)
        self.bus.datrd.setimmediatevalue(0)
        if hasattr(self.bus, "err"):        
            self.bus.err.setimmediatevalue(0)
        if hasattr(self.bus, "stall"): 
            self.bus.stall.setimmediatevalue(0) 
    
    @coroutine
    def _respond(self):
        pass
    
    @coroutine
    def receive_cycle(self, arg):
        pass
            

class WishboneSlave(Wishbone):
    """Wishbone slave
    """
    
    def bitSeqGen(self, tupleGen):
        while True: 
            [highCnt, lowCnt] = tupleGen.next()
                #make sure there's something in here            
            if lowCnt < 1:
                lowCnt = 1
            bits=[]
            for i in range(0, highCnt):
               bits.append(1)          
            for i in range(0, lowCnt):
               bits.append(0)
            for bit in bits:
                yield bit
    
    
    def defaultTupleGen():
        while True:        
            yield int(0), int(1)      
    
    def defaultGen():
        while True:        
            yield int(0)
            
    def defaultGen1():
        while True:        
            yield int(1)          
    
    _acked_ops      = 0  # ack cntr. wait for equality with number of Ops before releasing lock
    _reply_Q        = Queue.Queue() # save datwr, sel, idle
    _res_buf        = [] # save readdata/ack/err/rty
    _clk_cycle_count = 0
    _cycle = False
    _datGen         = defaultGen()
    _ackGen         = defaultGen1()
    _stallWaitGen   = defaultGen()
    _waitAckGen   = defaultGen()
    _lastTime       = 0
    _stallCount     = 0
    

    def __init__(self, *args, **kwargs):
        datGen = kwargs.pop('datgen', None)
        ackGen = kwargs.pop('ackgen', None)
        waitAckGen = kwargs.pop('replywaitgen', None)
        stallWaitGen = kwargs.pop('stallwaitgen', None)
        Wishbone.__init__(self, *args, **kwargs)
        cocotb.fork(self._stall())
        cocotb.fork(self._clk_cycle_counter())
        cocotb.fork(self._ack())
        self.log.info("Wishbone Slave created")
        
        if waitAckGen != None:
            self._waitAckGen  = waitAckGen 
        if stallWaitGen != None:
            self._stallWaitGen  = self.bitSeqGen(stallWaitGen)
        if ackGen != None:
            self._ackGen        = ackGen
        if datGen != None:
            self._datGen        = datGen
        
    
    @coroutine 
    def _clk_cycle_counter(self):
        """
        """
        clkedge = RisingEdge(self.clock)
        self._clk_cycle_count = 0
        while True:
            if self._cycle:
                self._clk_cycle_count += 1
            else:
                self._clk_cycle_count = 0
            yield clkedge
            

    @coroutine
    def _stall(self):
        clkedge = RisingEdge(self.clock)
        # if stall drops, keep the value for one more clock cycle
        while True:
            if hasattr(self.bus, "stall"):
                tmpStall = self._stallWaitGen.next()
                self.bus.stall <= tmpStall
                if bool(tmpStall):                                
                    self._stallCount += 1                    
                    yield clkedge
                else:
                    yield clkedge                    
                    self._stallCount = 0
            
            
        
    @coroutine
    def _ack(self):
        clkedge = RisingEdge(self.clock)         
        while True: 
            #set defaults
            self.bus.ack    <= 0
            self.bus.datrd  <= 0
            if hasattr(self.bus, "err"):
                self.bus.err <= 0
            if hasattr(self.bus, "rty"):
                self.bus.rty <= 0        
            
            if not self._reply_Q.empty():
                #get next reply from queue                    
                rep = self._reply_Q.get_nowait()
                
                #wait <waitAck> clock cycles before replying
                if rep.waitAck != None:
                    waitcnt = rep.waitAck
                    while waitcnt > 0:
                        waitcnt -= 1
                        yield clkedge
                
                #check if the signal we want to assign exists and assign
                if not hasattr(self.bus, self.replyTypes[rep.ack]):                
                    raise TestFailure("Tried to assign <%s> (%u) to slave reply, but this slave does not have a <%s> line" % (self.replyTypes[rep.ack], rep.ack, self.replyTypes[rep.ack]))
                if self.replyTypes[rep.ack]    == "ack":
                    self.bus.ack    <= 1
                elif self.replyTypes[rep.ack]  == "err":
                    self.bus.err    <= 1
                elif self.replyTypes[rep.ack]  == "rty":
                    self.bus.rty    <= 1
                self.bus.datrd  <= rep.datrd
            yield clkedge



    def _respond(self):
        valid =  bool(self.bus.cyc.getvalue()) and bool(self.bus.stb.getvalue())
        if hasattr(self.bus, "stall"):
                valid = valid and not bool(self.bus.stall.getvalue())
        
        if valid:
            #if there is a stall signal, take it into account
            #wait before replying ?    
            waitAck = self._waitAckGen.next()
            #Response: rddata/don't care        
            if (not bool(self.bus.we.getvalue())):
                rd = self._datGen.next()
            else:
                rd = 0
         
            #Response: ack/err/rty
            reply = self._ackGen.next()
            if reply not in self.replyTypes:
                raise TestFailure("Tried to assign unknown reply type (%u) to slave reply. Valid is 1-3 (ack, err, rty)" %  reply)
            
            wr = None
            if bool(self.bus.we.getvalue()):
                wr = self.bus.datwr.getvalue()
            
            #get the time the master idled since the last operation
            #TODO: subtract our own stalltime or, if we're not pipelined, time since last ack    
            idleTime = self._clk_cycle_count - self._lastTime -1    
            res =  WBRes(ack=reply, sel=self.bus.sel.getvalue(), adr=self.bus.adr.getvalue(), datrd=rd, datwr=wr, waitIdle=idleTime, waitStall=self._stallCount, waitAck=waitAck)               
            #print "#ADR: 0x%08x,0x%x DWR: %s DRD: %s REP: %s IDL: %3u STL: %3u RWA: %3u" % (res.adr, res.sel, res.datwr, res.datrd, replyTypes[res.ack], res.waitIdle, res.waitStall, res.waitAck)       
            
           #add whats going to happen to the result buffer
            self._res_buf.append(res)
            #add it to the reply queue for assignment. we need to process ops every cycle, so we can't do the <waitreply> delay here
            self._reply_Q.put(res)
            self._lastTime = self._clk_cycle_count
            
            

    @coroutine
    def _monitor_recv(self):
        clkedge = RisingEdge(self.clock)
  
        #respong and notify the callback function  
        while True:
            if int(self._cycle) < int(self.bus.cyc.getvalue()):
                self._lastTime = self._clk_cycle_count -1
                
            self._respond()
            if int(self._cycle) > int(self.bus.cyc.getvalue()):
                self._recv(self._res_buf)
                self._reply_Q.queue.clear()
                self._res_buf = []
                
            self._cycle = self.bus.cyc.getvalue()
            yield clkedge