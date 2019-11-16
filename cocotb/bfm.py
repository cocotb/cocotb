
import os

if "COCOTB_SIM" in os.environ:
    import simulator

class Bfm():
    
    def __init__(self):
        self.method_l = []
        pass
    
    def call_method(self, id, params):
        self.method_l[id](self, *params)


class BfmMgr():
    
    m_inst = None
    
    def __init__(self):
        self.bfm_l = []
        n_bfms = simulator.bfm_get_count()
        print("n_bfms: " + str(n_bfms))
        for i in range(n_bfms):
            info = simulator.bfm_get_info(i)
            typename = info[0]
            clsname = info[2]
            print("info " + str(i) + " " + str(info))
        pass
    
    @staticmethod
    def get_bfms():
        return BfmMgr.inst().bfm_l
   
    @staticmethod
    def inst():
        if BfmMgr.m_inst == None:
            BfmMgr.m_inst = BfmMgr()
            
        return BfmMgr.m_inst
    
    @staticmethod    
    def init():
        simulator.bfm_set_call_method(BfmMgr.call)
        BfmMgr.inst()
        
    @staticmethod
    def call(bfm_id, method_id, params):
        inst = BfmMgr.inst()
        bfm = inst.bfm_l[bfm_id].call_method(method_id, params)
