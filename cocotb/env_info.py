###############################################################################
# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
###############################################################################

class EnvInfo():
    """Collects information about the environment in which cocotb is running"""
    
    def __init__(self):
        self.sim_name    = "unknown"
        self.sim_version = "unknown"
        self.argv = []
    
    def set_sim_name(self, name):
        self.sim_name = name
        
    def get_sim_name(self, name):
        return self.sim_name
    
    def set_sim_version(self, version):
        self.sim_version = version
        
    def get_sim_version(self, version):
        return self.sim_version
