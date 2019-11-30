
import cocotb
from cocotb.triggers import Timer
from rv_bfms import * 

class BfmTest(ReadyValidDataMonitorIF):

    def __init__(self):
        self.data_l = []

    def data_recv(self, d):
        self.data_l.append(d)

    @cocotb.coroutine
    def run(self):
        bfm = cocotb.BfmMgr.find_bfm(".*u_dut")
        mon = cocotb.BfmMgr.find_bfm(".*u_mon")

        mon.add_listener(self)

        # Send data out via the BFM
        for i in range(100):
            yield bfm.write_c(i)

        yield Timer(10)

        if len(self.data_l) != 100:
            raise TestError("len (%d) != 100" % len(self.data_l))

@cocotb.test()
def runtest(dut):
  test = BfmTest()
  yield test.run()



