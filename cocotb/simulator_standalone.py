###############################################################################
# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
###############################################################################

from cocotb.simulator_base import SimulatorBase
import cocotb

class SimulatorStandalone(SimulatorBase):
    """Pure-Python implementation of the simulator backend

    This is used when running cocotb without a simulator, 
    typically for the purposes of unit-testing a library
    on top of cocotb.
    """
    
    def __init__(self):
        super().__init__()
        self.timewheel = [] # list of time,callback tuples
        self.time_ps = 0

    def run(self):
        base_time = -1
        ret = len(self.timewheel) > 0
        
        if ret:
            base_time = self.timewheel[0][0]
            self.time_ps += base_time
            
        while len(self.timewheel) > 0:
            top = self.timewheel.pop()
            
            try:
                top[1](*top[2])
            except Exception as e:
                cocotb.log.exception(e)
                
            if len(self.timewheel) > 0 and self.timewheel[0][0] > 0:
                # Reached the end of the current timestep
                break

        return ret

    def register_timed_callback(self, sim_steps, callback, *args):
        
        if len(self.timewheel) == 0:
            self.timewheel.append([sim_steps, callback, args])
        else:
            for i in range(len(self.timewheel)):
                if (sim_steps > self.timewheel[i][0]):
                    sim_steps -= self.timewheel[i][0]
                    
                    if (i+1) >= len(self.timewheel):
                        self.timewheel.append([sim_steps, callback, args])
                else:
                    offset = self.timewheel[i][0]
                    offset -= sim_steps
                    self.timewheel[i][0] = offset
                    self.timewheel.insert(i, [sim_steps, callback, args])

    def get_precision(self):
        return -12 # pS
    
    def get_sim_time(self):
        return (self.time_ps >> 32, self.time_ps & 0xFFFFFFFF)
