import cocotb
from cocotb.triggers import Timer
from cocotb.result import TestError, TestFailure
from cocotb.handle import *

import logging
import pprint
import textwrap

# NOTE: port discovery needs SINGLETON_HANDLES in lib/gpi/Makefile not set!

@cocotb.test()
def create_testbench_template(dut):
    """Generate a testbench template for the DUT."""

    yield Timer(0)  # needed to make this a valid coroutine

    input_ports_=[]
    output_ports_=[]
    inout_ports_=[]
    supply_ports_=[]
    ground_ports_=[]
    clock_ports_=[]
    reset_ports_=[]
    for thing_ in dut:
        if isinstance(thing_, HierarchyObject) and thing_._is_port:
            dut._log.info('{} Port {}'.format(thing_._port_direction_string[4:].capitalize(), thing_._path))
            if thing_._port_direction_string == 'GPI_INPUT':
                input_ports_.append(thing_)
            elif thing_._port_direction_string == 'GPI_OUTPUT':
                output_ports_.append(thing_)
            elif thing_._port_direction_string == 'GPI_INOUT':
                inout_ports_.append(thing_)
            else:
                dut._log.info('Unhandled port direction {} of {}!'.format(thing_._port_direction_string, thing_._path))

    # match names to identify "special" ports:
    for port_ in set(input_ports_+inout_ports_):
        if port_._name.startswith('vd') or port_._name.startswith('vc'):
            # Examples: vdd, vddd, vdda, vdio, vcc, vcore
            dut._log.info('Identified a supply port: {}'.format(port_._name))
            supply_ports_.append(port_)
        elif port_._name.startswith('vs') or port_._name.startswith('gnd') or port_._name.endswith('gnd'):
            # Examples: gnd, agnd, dgnd, vs, vss, vssd, vsio
            dut._log.info('Identified a ground port: {}'.format(port_._name))
            ground_ports_.append(port_)
        elif (port_._name.startswith('clk') or port_._name.endswith('clk')
              or port_._name.startswith('clock') or port_._name.endswith('clock')):
            # Examples: clk_2MHz, clk_main, main_clk, main_clock
            dut._log.info('Identified a clock: {}'.format(port_._name))
            clock_ports_.append(port_)
        elif port_._name in ('reset', 'resetn', 'reset_n', 'rst', 'rstn', 'rst_n'):
            # Examples: exactly these
            dut._log.info('Identified a reset: {}'.format(port_._name))
            reset_ports_.append(port_)

    # clean up original lists:
    for port_ in supply_ports_+ground_ports_+clock_ports_+reset_ports_:
        try:
            input_ports_.remove(port_)
        except:
            pass
        try:
            inout_ports_.remove(port_)
        except:
            pass

    filename_ = os.getenv('COCOTB_TESTBENCH_TEMPLATE')
    if filename_ is None:
        filename_ = 'testbench_template'

    with open(filename_+'.py', 'w') as f:
        f.write(textwrap.dedent("""
            # This is a generated testbench template for cocotb (https://cocotb.readthedocs.io)
            
            import cocotb
            from cocotb.triggers import (Timer, Join, RisingEdge, FallingEdge, Edge,
                                         ReadOnly, ReadWrite, ClockCycles, NextTimeStep)
            from cocotb.binary import BinaryValue
            from cocotb.clock import Clock
            from cocotb.result import ReturnValue, TestFailure, TestError, TestSuccess
            
            # TODO: adapt these constants
            CLOCK_PERIOD_NS = 2
            PRE_RESET_TIME_NS = 1
            RESET_DURATION_NS = 7
            
            @cocotb.test()
            def my_first_test(dut):
                \"\"\"TODO: Add test documentation here.\"\"\"
            
                import cocotb.wavedrom
            
                dut._log.info("Running my first test")\n"""))

        f.write('\n')
        f.write('    dut._log.info("Setting ground ports if any were identified")\n')
        for port_ in ground_ports_:
            f.write('    dut.{} <= 0\n'.format(port_._name))
        if len(ground_ports_) == 0:
            f.write('    # dut.{} <= 0\n'.format('<port>'))

        f.write('\n')
        f.write('    dut._log.info("Setting supply ports if any were identified")\n')
        for port_ in supply_ports_:
            f.write('    dut.{} <= 1\n'.format(port_._name))
        if len(supply_ports_) == 0:
            f.write('    # dut.{} <= 1\n'.format('<port>'))

        f.write('\n')
        f.write('    dut._log.info("Asserting and de-asserting reset(s) if any were identified (assuming active-low resets!)")\n')
        for port_ in reset_ports_:
            f.write("""    dut.{} <= 1
    yield Timer(PRE_RESET_TIME_NS, units='ns')
    dut.{} <= 0
    yield Timer(RESET_DURATION_NS, units='ns')
    dut.{} <= 1\n""".format(port_._name, port_._name, port_._name))
        if len(reset_ports_) == 0:
            f.write("""    # dut.{} <= 1
    # yield Timer(PRE_RESET_TIME_NS, units='ns')
    # dut.{} <= 0
    # yield Timer(RESET_DURATION_NS, units='ns')
    # dut.{} <= 1\n""".format('<port>', '<port>', '<port>'))

        f.write('\n')
        f.write('    dut._log.info("Starting clocks if any were identified")\n')
        for port_ in clock_ports_:
            f.write("    cocotb.fork(Clock(dut.{}, CLOCK_PERIOD_NS, units='ns').start())\n".format(port_._name))
        if len(clock_ports_) == 0:
            f.write("    # cocotb.fork(Clock(dut.{}, CLOCK_PERIOD_NS, units='ns').start())\n".format('<port>'))

        f.write('\n')
        f.write('    waves = cocotb.wavedrom.trace(\n')
        for port_ in input_ports_+inout_ports_+output_ports_:
            f.write('        dut.{},\n'.format(port_._name))
        f.write('        clk=dut.clk)\n')

        f.write('\n')
        f.write('    dut._log.info("Driving all other DUT inputs and inouts if any are present")\n')
        f.write('    # Changes needed for real signals (drive with "0.0"), and struct/record ports\n')
        driveable_ports_ = input_ports_+inout_ports_
        for port_ in driveable_ports_:
            f.write('    dut.{} <= 0x0\n'.format(port_._name))
        if len(driveable_ports_) == 0:
            f.write('    # dut.{} <= 0x0\n'.format('<port>'))

        f.write('\n')
        f.write('    dut._log.info("Waiting for some rising edges on all clock signals")\n')
        for port_ in clock_ports_:
            f.write('    yield ClockCycles(dut.{}, 3)\n'.format(port_._name))
            f.write('    yield RisingEdge(dut.{})\n'.format(port_._name))
        if len(clock_ports_) == 0:
            f.write('    # yield ClockCycles(dut.{}, 3)\n'.format('<port>'))
            f.write('    # yield RisingEdge(dut.{})\n'.format('<port>'))

        f.write('\n')
        f.write('    # yield ReadOnly()  # wait until all events have executed for this timestep\n')

        f.write('\n')
        f.write('    dut._log.info("Reading all DUT outputs and inouts if any are present")\n')
        f.write('    # can also use int(port._name)\n')

        readable_ports_ = output_ports_+inout_ports_
        for port_ in readable_ports_:
            f.write('    {} = dut.{}.value.binstr\n'.format(port_._name+'_val', port_._name))
        if len(readable_ports_) == 0:
            f.write('    # {} = dut.{}.value.binstr\n'.format('<port>'+'_val', '<port>'))
        for port_ in readable_ports_:
            f.write("""    dut._log.info("{} = {{}}".format(str({})))\n""".format(port_._name, port_._name+'_val'))
        if len(readable_ports_) == 0:
            f.write("""    # dut._log.info("{} = {{}}".format(str({})))\n""".format('<port>', '<port>'+'_val'))

        f.write("""
    dut._log.info("Waiting 10 ns...")
    yield Timer(10, units='ns')
    dut._log.info("Waiting 10 ns...done")\n""")

        f.write('    dut._log.info(waves.write("{}"))\n'.format(filename_+'.wavedrom.json'))
    dut._log.warning('Wrote testbench template {}'.format(filename_+'.py'))
    try:
        dut._log.warning('Try running with\n    make {} MODULE=testbench_template'.format(os.getenv("MAKEFLAGS")[5:]))
    except:
        pass
