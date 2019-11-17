
import os
import importlib

if "COCOTB_SIM" in os.environ:
    import simulator
    
import_info_l = []
export_info_l = []

def register_bfm_type(T):
    global import_info_l
    global export_info_l
    print("register_bfm_type: " + str(T))
    type_info = BfmTypeInfo(import_info_l.copy(), export_info_l.copy())
    BfmMgr.inst().add_type_info(T, type_info)
    import_info_l = []
    export_info_l = []
    
def register_bfm_import_info(info):
    global import_info_l
    info.id = len(import_info_l)
    import_info_l.append(info)
    
def register_bfm_export_info(info):
    global export_info_l
    info.id = len(import_info_l)
    export_info_l.append(info)

class BfmMethodInfo():
    
    def __init__(self, T, signature):
        self.T = T
        self.signature = signature
        self.id = -1

class BfmTypeInfo():
    
    def __init__(self, import_info, export_info):
        self.import_info = import_info
        self.export_info = export_info

class BfmInfo():
    
    def __init__(self, id, type_info):
        self.id = id
        self.type_info = type_info
        
    def call_method(self, method_id, params):
        self.type_info.export_import[method_id].T(*params)

class BfmMgr():
    
    m_inst = None
    
    def __init__(self):
        self.bfm_l = []
        self.bfm_type_info_m = {}
        pass
    
    def add_type_info(self, T, type_info):
        self.bfm_type_info_m[T] = type_info
    
    @staticmethod
    def get_bfms():
        return BfmMgr.inst().bfm_l
   
    @staticmethod
    def inst():
        if BfmMgr.m_inst == None:
            BfmMgr.m_inst = BfmMgr()
            
        return BfmMgr.m_inst
   
    def load_bfms(self):
        n_bfms = simulator.bfm_get_count()
        print("n_bfms: " + str(n_bfms))
        for i in range(n_bfms):
            info = simulator.bfm_get_info(i)
            typename = info[0]
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
            bfm_info = BfmInfo(len(self.bfm_l), type_info)
            
            bfm = bfmcls()
            # Add 
            setattr(bfm, "bfm_info", bfm_info)
            
            self.bfm_l.append(bfm)
    
    @staticmethod    
    def init():
        simulator.bfm_set_call_method(BfmMgr.call)
        BfmMgr.inst().load_bfms()
        
    @staticmethod
    def call(bfm_id, method_id, params):
        inst = BfmMgr.inst()
        bfm = inst.bfm_l[bfm_id]
        
        if not hasattr(bfm, "bfm_info"):
            raise Exception("BFM object does not contain 'bfm_info' field")

        bfm.bfm_info.call_method(method_id, params)
