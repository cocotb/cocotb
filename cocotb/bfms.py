###############################################################################
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Copyright (c) 2019 Matthew Ballance
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd,
#       SolarFlare Communications Inc nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
###############################################################################

import os
import importlib
import re
from cocotb.decorators import bfm_param_int_t

import_info_l = []
export_info_l = []

def register_bfm_type(T, hdl):
    global import_info_l
    global export_info_l
    
    type_info = BfmTypeInfo(T, hdl, import_info_l.copy(), export_info_l.copy())
    BfmMgr.inst().add_type_info(T, type_info)
    import_info_l = []
    export_info_l = []
    
def register_bfm_import_info(info):
    global import_info_l
    info.id = len(import_info_l)
    import_info_l.append(info)
    
def register_bfm_export_info(info):
    global export_info_l
    info.id = len(export_info_l)
    export_info_l.append(info)
    
def bfm_hdl_path(py_file, template):
    return os.path.join(
        os.path.dirname(os.path.abspath(py_file)),
        template)

class BfmMethodParamInfo():
    '''
    Information about a single BFM-method parameter
    '''
    
    def __init__(self, pname, ptype):
        self.pname = pname
        self.ptype = ptype

class BfmMethodInfo():
    '''
    Information about a single BFM method
    - Method type
    - User-specified parameter signature
    '''
    
    def __init__(self, T, signature):
        fullname = T.__qualname__
        fi = T.__code__
        
        self.T = T
        self.signature = []
        self.type_info = []
        self.id = -1

        locals_idx = fullname.find("<locals>")
        if locals_idx != -1:
            fullname = fullname[locals_idx+len("<locals>."):]
            
        if fullname.find('.') == -1:
            raise Exception("Attempting to register a global method as a BFM method")
        
        args = fi.co_varnames[1:fi.co_argcount]
        if len(signature) != len(args):
            raise Exception("Wrong number of parameter-type elements: expect " + str(len(args)) + " but received " + str(len(signature)))
        
        
        for i in range(len(args)):
            a = args[i]
            t = signature[i]
            self.signature.append(BfmMethodParamInfo(a, t))
            try:
                import simulator
                if isinstance(t, bfm_param_int_t):
                    if t.s:
                        self.type_info.append(simulator.BFM_SI_PARAM)
                    else:
                        self.type_info.append(simulator.BFM_UI_PARAM)
            except Exception:
                # When we're not running in simulation, don't 
                # worry about being able to access constants from simulation
                self.type_info.append(None)
                pass


class BfmTypeInfo():
    
    def __init__(self, T, hdl, import_info, export_info):
        self.T = T
        self.hdl = hdl
        self.import_info = import_info
        self.export_info = export_info

class BfmInfo():
    
    def __init__(self, bfm, id, inst_name, type_info):
        self.bfm = bfm
        self.id = id
        self.inst_name = inst_name
        self.type_info = type_info
        
    def call_method(self, method_id, params):
        self.type_info.export_info[method_id].T(
            self.bfm, *params)

class BfmMgr():
    
    m_inst = None
    
    def __init__(self):
        self.bfm_l = []
        self.bfm_type_info_m = {}
        self.m_initialized = False
    
    def add_type_info(self, T, type_info):
        self.bfm_type_info_m[T] = type_info
    
    @staticmethod
    def get_bfms():
        return BfmMgr.inst().bfm_l

    @staticmethod    
    def find_bfm(path_pattern):
        inst = BfmMgr.inst()
        bfm = None
       
        path_pattern_re = re.compile(path_pattern)
        
        for b in inst.bfm_l:
            if path_pattern_re.match(b.bfm_info.inst_name):
                bfm = b
                break
        
        return bfm
   
    @staticmethod
    def inst():
        if BfmMgr.m_inst == None:
            BfmMgr.m_inst = BfmMgr()
            
        return BfmMgr.m_inst
   
    def load_bfms(self):
        '''
        Obtain the list of BFMs from the native layer
        '''
        import simulator
        n_bfms = simulator.bfm_get_count()
        for i in range(n_bfms):
            info = simulator.bfm_get_info(i)
            typename = info[0]
            instname = info[1]
            clsname = info[2]
            if clsname.find('.') == -1:
                raise Exception("Incorrectly-formatted BFM class name \"" + clsname + "\"")
            pkgname = clsname[:clsname.rfind('.')]
            clsleaf = clsname[clsname.rfind('.')+1:]
          
            try: 
                pkg = importlib.import_module(pkgname)
            except Exception as e:
                raise Exception("Failed to import BFM package \"" + pkgname + "\"")
       
            if not hasattr(pkg, clsleaf):
                raise Exception("Failed to find BFM class \"" + clsleaf + "\" in package \"" + pkgname + "\"") 

            bfmcls = getattr(pkg, clsleaf)
            
            type_info = self.bfm_type_info_m[bfmcls]
            
            bfm = bfmcls()
            bfm_info = BfmInfo(
                bfm, 
                len(self.bfm_l), 
                instname,
                type_info)
            # Add 
            setattr(bfm, "bfm_info", bfm_info)
            
            self.bfm_l.append(bfm)
    
    @staticmethod    
    def init():
        import simulator
        inst = BfmMgr.inst()
        if not inst.m_initialized:
            simulator.bfm_set_call_method(BfmMgr.call)
            BfmMgr.inst().load_bfms()
            inst.m_initialized = True
        
    @staticmethod
    def call(
            bfm_id, 
            method_id,
            params):
        inst = BfmMgr.inst()
        bfm = inst.bfm_l[bfm_id]
         
        if not hasattr(bfm, "bfm_info"):
            raise Exception("BFM object does not contain 'bfm_info' field")
 
        bfm.bfm_info.call_method(method_id, params)

    
