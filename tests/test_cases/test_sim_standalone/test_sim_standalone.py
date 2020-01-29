###############################################################################
# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
###############################################################################

from unittest.case import TestCase
import cocotb
import logging
from cocotb.log import SimLog
from cocotb.triggers import Event, Timer
from cocotb.scheduler import Scheduler
from cocotb.utils import get_sim_time

class TestSimStandalone(TestCase):

    class SimulatorStub():
        """Implements minimum of the simulator API

           The API is sufficient for the cocotb scheduler to be run standalone
           without being within a real HDL simulator
        """

        def __init__(self):
            self.timewheel = [] # list of time,callback,id tuples
            self.time_ps = 0
            self.cb_id = 1

        def register_timed_callback(self, sim_steps, callback, *args):
            ret = self.cb_id
            inserted = False
        
            for i in range(len(self.timewheel)):
                if (sim_steps > self.timewheel[i][0]):
                    sim_steps -= self.timewheel[i][0]
                elif i+1 < len(self.timewheel) and self.timewheel[i+1][0] > sim_steps:
                    offset = self.timewheel[i][0]
                    offset -= sim_steps
                    self.timewheel[i][0] = offset
                    self.timewheel.insert(i, [sim_steps, callback, args, ret])
                    inserted = True
                    break
            
            if not inserted:
                self.timewheel.append([sim_steps, callback, args, ret])
                
            self.cb_id += 1
        
            return ret

        def deregister_callback(self, hndl):
            for i in range(len(self.timewheel)):
                if self.timewheel[i][3] == hndl:
                    self.timewheel.pop(i)
                    break

        def run(self):
            base_time = -1
            ret = len(self.timewheel) > 0
        
            if ret:
                base_time = self.timewheel[0][0]
                self.time_ps += base_time
            
            while len(self.timewheel) > 0:
                top = self.timewheel.pop(0)
                top[1](*top[2])
                
                if len(self.timewheel) > 0 and self.timewheel[0][0] > 0:
                    # Reached the end of the current timestep
                    break

            return ret

        def get_precision(self):
            return -12 # pS
    
        def get_sim_time(self):
            return (self.time_ps >> 32, self.time_ps & 0xFFFFFFFF)

    class MB():
        def __init__(self):
            self.p2c_ev = Event()
            self.c2p_ev = Event()
            self.p2c = 0
            self.c2p = 0
            
        def send_p2c(self):
            self.p2c_ev.set()

        @cocotb.coroutine        
        def get_c2p(self):
            yield self.c2p_ev.wait()
            self.c2p_ev.clear()
            self.c2p += 1
        
        def send_c2p(self):
            self.c2p_ev.set()

        @cocotb.coroutine        
        def get_p2c(self):
            yield self.p2c_ev.wait()
            self.p2c_ev.clear()
            self.p2c += 1
    
    def test_simple_pingpong(self):
        """Runs a series of untimed ping-pongs"""
        
        @cocotb.coroutine
        def producer(mb):
            for i in range(16):
                mb.send_p2c()
                yield mb.get_c2p()
            
        @cocotb.coroutine
        def consumer(mb):
            for i in range(16):
                yield mb.get_p2c()
                mb.send_c2p()

        @cocotb.test()
        def test_main():
            mb = TestSimStandalone.MB()
            t_c1 = cocotb.fork(producer(mb))
            t_c2 = cocotb.fork(consumer(mb))
            yield [t_c1.join(), t_c2.join()]
            self.assertEqual(mb.p2c, 16)
            self.assertEqual(mb.c2p, 16)
        
        sim = TestSimStandalone.SimulatorStub()
        cocotb.simulator = sim
        cocotb.scheduler = Scheduler()
        cocotb.log = SimLog("cocotb")
        cocotb.argv = []
        cocotb.process_plusargs()
        cocotb.log.setLevel(logging.INFO)        
        
        cocotb.scheduler.add_test(test_main())

        # This will run the test-completed callback
        sim.run()
        
    
    def test_timed_pingpong(self):
        """Runs a series of timed ping-pongs"""
        
        @cocotb.coroutine
        def producer(mb):
            for i in range(16):
                mb.send_p2c()
                yield mb.get_c2p()
                yield Timer(10)
            
        @cocotb.coroutine
        def consumer(mb):
            for i in range(16):
                yield mb.get_p2c()
                mb.send_c2p()
                yield Timer(20)

        @cocotb.test()
        def test_main(mb):
            t_c1 = cocotb.fork(producer(mb))
            t_c2 = cocotb.fork(consumer(mb))
            yield [t_c1.join(), t_c2.join()]
            self.assertEqual(mb.p2c, 16)
            self.assertEqual(mb.c2p, 16)
        
        mb = TestSimStandalone.MB()
        sim = TestSimStandalone.SimulatorStub()
        
        cocotb.simulator = sim
        cocotb.scheduler = Scheduler()
        cocotb.fork = cocotb.scheduler.add
        cocotb.log = SimLog("cocotb")
        cocotb.argv = []
        cocotb.process_plusargs()
        cocotb.log.setLevel(logging.INFO)                
        
        cocotb.scheduler.add_test(test_main(mb))
       
        # The consumer and producer wait after each transfer.
        # Consequently, only the first will be complete 
        # at this time. 
        self.assertEqual(mb.p2c, 1)
        self.assertEqual(mb.c2p, 1)

        # This will run the test-completed callback
        while sim.run():
            pass
        
        # Ensure the full run completed
        self.assertEqual(mb.p2c, 16)
        self.assertEqual(mb.c2p, 16)
