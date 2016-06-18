########
Examples
########

These code samples show some typical usage of Cocotb based on real-world problems.


Example testbench for snipped of code from `comp.lang.verilog <https://github.com/chiggs/comp.lang.verilog/blob/master/maja55/testbench.py>`_:

.. code-block:: python

    @cocotb.coroutine
    def run_test(dut, data_generator=random_data, delay_cycles=2):
        """
        Send data through the DUT and check it is sorted out output
        """
        cocotb.fork(Clock(dut.clk, 100).start())

        # Don't check until valid output
        expected = [None] * delay_cycles

        for index, values in enumerate(data_generator(bits=len(dut.in1))):
            expected.append(sorted(values))

            yield RisingEdge(dut.clk)
            dut.in1 = values[0]
            dut.in2 = values[1]
            dut.in3 = values[2]
            dut.in4 = values[3]
            dut.in5 = values[4]

            yield ReadOnly()
            expect = expected.pop(0)

            if expect is None: continue


            got = [int(dut.out5), int(dut.out4), int(dut.out3),
                   int(dut.out2), int(dut.out1)]

            if got != expect:
                dut._log.error('Expected %s' % expect)
                dut._log.error('Got %s' % got)
                raise TestFailure("Output didn't match")

        dut._log.info('Sucessfully sent %d cycles of data' % (index + 1))


