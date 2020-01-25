###############################################################################
# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
###############################################################################
from cocotb.scheduler import Scheduler
from cocotb.log import SimLog

class ExecContext():
    """Collects core cocotb execution elements"""
    
    def __init__(self, info, sim):
        self.info = info
        self.simulator = sim
        self.scheduler = Scheduler()
        self.log = SimLog('cocotb')
        
    def start_test(self, test_coro):
        """Called to run the main test coroutine
        
        This method is used when cocotb is run in standalone mode
        """
        self.scheduler.add_test(test_coro)