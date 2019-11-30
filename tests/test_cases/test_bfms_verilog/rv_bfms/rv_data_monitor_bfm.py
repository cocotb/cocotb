'''
Created on Oct 6, 2019

@author: ballance
'''

import cocotb
from cocotb.drivers import Driver
from cocotb.triggers import RisingEdge, ReadOnly, Lock, Event


@cocotb.bfm(hdl={
    cocotb.bfm_vlog : cocotb.bfm_hdl_path(__file__, "hdl/rv_data_monitor_bfm.v"),
    cocotb.bfm_sv   : cocotb.bfm_hdl_path(__file__, "hdl/rv_data_monitor_bfm.v")
    })
class ReadyValidDataMonitorBFM():

    def __init__(self):
        self.listener_l = []
        
    
    def add_listener(self, l):
        self.listener_l.append(l)

    @cocotb.bfm_export(cocotb.bfm_uint64_t)
    def data_recv(self, d):
        for l in self.listener_l:
            l.data_recv(d)
    
