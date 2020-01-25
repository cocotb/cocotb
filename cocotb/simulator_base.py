###############################################################################
# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
###############################################################################

class SimulatorBase():
    """
    Defines the API that simulators are expected to provide 
    """
    
    def __init__(self):
        pass
    
    def log_msg(self, name, path, funcname, lineno, msg):
        """Causes the simulator to display a message"""
        
    def get_signal_val_long(self, o):
        """Gets the long-int value of the specified signal handle"""
        
    def get_signal_val_str(self, o):
        """Gets the string value of the specified signal handle"""
        
    def register_timed_callback(self, sim_steps, callback, hndl):
        """Register a callback to be delivered after 'sim_steps' time"""
    
    def log_level(self, l):
        """Sets the logging level"""
        
    def get_sim_time(self):
        """Returns the current time time in a (high,low) tuple"""
        return (0,0)
        
    def get_precision(self):
        """Returns time precision as an integer"""
        return -9 # ns
    
    def deregister_callback(self, hndl):
        """Removes a previously-registered callback"""
        
    def error_out(self):
        """Issue a fatal error"""