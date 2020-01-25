###############################################################################
# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
###############################################################################

from unittest.case import TestCase
from cocotb.simulator_standalone import SimulatorStandalone
from cocotb.env_info import EnvInfo
import cocotb
from cocotb.triggers import Event, Timer
from cocotb.utils import get_sim_time

class TestSimStandalone(TestCase):
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

        @cocotb.coroutine
        def test_main():
            mb = TestSimStandalone.MB()
            t_c1 = cocotb.fork(producer(mb))
            t_c2 = cocotb.fork(consumer(mb))
            yield [t_c1.join(), t_c2.join()]
            self.assertEqual(mb.p2c, 16)
            self.assertEqual(mb.c2p, 16)
        
        sim = SimulatorStandalone()
        info = EnvInfo()
        
        exec_ctxt = cocotb.initialize_exec_context(info, sim)
        exec_ctxt.start_test(test_main())

        self.assertEqual(get_sim_time(), 0)
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

        @cocotb.coroutine
        def test_main(mb):
            t_c1 = cocotb.fork(producer(mb))
            t_c2 = cocotb.fork(consumer(mb))
            yield [t_c1.join(), t_c2.join()]
            self.assertEqual(mb.p2c, 16)
            self.assertEqual(mb.c2p, 16)
        
        sim = SimulatorStandalone()
        info = EnvInfo()
        
        mb = TestSimStandalone.MB()
        exec_ctxt = cocotb.initialize_exec_context(info, sim)
        exec_ctxt.start_test(test_main(mb))
       
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
