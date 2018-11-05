import cocotb
from cocotb.triggers import Timer
from cocotb.result import TestError, TestFailure
from cocotb.handle import *

import logging
import pprint

# FIXME: port stuff needs SINGLETON_HANDLES in lib/gpi/Makefile not set!


def get_name_maxlen(objlist):
    '''
    Return the longest name of a list of objects.
    '''
    try:
        return max(len(x._name) for x in objlist)
    except:
        return 0


@cocotb.test()
def create_testbench_template(dut, filename='testbench_template.py'):
    '''
    Generate a testbench template for the DUT.
    '''
    
    yield Timer(0)  # needed to make this a valid coroutine

    input_ports=[]
    output_ports=[]
    inout_ports=[]
    supply_ports=[]
    ground_ports=[]
    clock_ports=[]
    reset_ports=[]
    for thing_ in dut:
        if isinstance(thing_, HierarchyObject) and thing_._is_port:
            dut._log.info('%s Port %s' % (thing_._port_direction_string[4:].capitalize(), thing_._path))
            if thing_._port_direction_string == 'GPI_INPUT':
                input_ports.append(thing_)
            elif thing_._port_direction_string == 'GPI_OUTPUT':
                output_ports.append(thing_)
            elif thing_._port_direction_string == 'GPI_INOUT':
                inout_ports.append(thing_)
                input_ports.append(thing_)
                output_ports.append(thing_)
            else:
                dut._log.info('Unhandled port direction %s of %s!' % (thing_._port_direction_string, thing_._path))

    # match names to identify "special" ports:
    for port_ in input_ports+inout_ports:
        if port_._name.startswith('vd') or port_._name.startswith('vc'):
            # Examples: vdd, vddd, vdda, vdio, vcc, vcore
            dut._log.info('Identified a supply port: %s' % (port_._name))
            supply_ports.append(port_)
        elif port_._name.startswith('vs') or port_._name.startswith('gnd') or port_._name.endswith('gnd'):
            # Examples: gnd, agnd, dgnd, vs, vss, vssd, vsio
            dut._log.info('Identified a ground port: %s' % (port_._name))
            ground_ports.append(port_)
        elif (port_._name.startswith('clk') or port_._name.endswith('clk')
              or port_._name.startswith('clock') or port_._name.endswith('clock')):
            # Examples: clk_2MHz, clk_main, main_clk, main_clock
            dut._log.info('Identified a clock: %s' % (port_._name))
            clock_ports.append(port_)
        elif port_._name in ('reset', 'reset_n', 'rst', 'rst_n'):
            # Examples: exactly these
            dut._log.info('Identified a reset: %s' % (port_._name))
            reset_ports.append(port_)

    with open(filename, 'w') as f:
        f.write('''# This is a generated testbench template for Cocotb (https://cocotb.readthedocs.io)

import cocotb
from cocotb.triggers import (Timer, Join, RisingEdge, FallingEdge, Edge,
                             ReadOnly, ReadWrite, ClockCycles, NextTimeStep)
from cocotb.binary import BinaryValue
from cocotb.clock import Clock
from cocotb.result import ReturnValue, TestFailure, TestError, TestSuccess

# TODO: adapt these constants
CLOCK_PERIOD_NS = 2
RESET_DURATION_NS = 7

# FIXME: recommended to make a class

@cocotb.test()
def my_first_test(dut):
    """
    TODO: Add test documentation here.
    """

    dut._log.info("Running my first test")\n''')

        f.write('\n')
        f.write('    dut._log.info("Asserting and de-asserting identified reset(s) (assuming active-low resets)")\n')
        for port_ in reset_ports:
            f.write('''    dut.%s <= 0
    yield Timer(RESET_DURATION_NS, units='ns')
    dut.%s <= 1\n''' % (port_._name, port_._name))
        if len(reset_ports) == 0:
            f.write('    dut._log.info("    <none>")\n')
            
        f.write('\n')
        f.write('    dut._log.info("Setting identified supply ports")\n')
        for port_ in supply_ports:
            f.write('    dut.%s <= 1\n' % (port_._name))
        if len(supply_ports) == 0:
            f.write('    dut._log.info("    <none>")\n')
            
        f.write('\n')
        f.write('    dut._log.info("Setting identified ground ports")\n')
        for port_ in ground_ports:
            f.write('    dut.%s <= 0\n' % (port_._name))
        if len(ground_ports) == 0:
            f.write('    dut._log.info("    <none>")\n')

        f.write('\n')
        f.write('    dut._log.info("Starting identified clock(s)")\n')
        for port_ in clock_ports:
            f.write(f"    cocotb.fork(Clock(dut.%s, CLOCK_PERIOD_NS, units='ns').start())\n" % (port_._name))
        if len(clock_ports) == 0:
            f.write('    dut._log.info("    <none>")\n')

        f.write('\n')
        f.write('    dut._log.info("Driving all remaining DUT inputs/inouts")\n')
        f.write('    # Changes needed for real signals (drive with "0.0"), and struct/record ports\n')
        remaining_ports = list(set(input_ports+inout_ports) -
                               set(supply_ports+ground_ports+clock_ports+reset_ports))
        maxlen = get_name_maxlen(remaining_ports)
        for port_ in remaining_ports:
            f.write('    dut.%s <= 0x0\n' % (port_._name.ljust(maxlen)))
        if len(remaining_ports) == 0:
            f.write('    dut._log.info("    <none>")\n')
        
        f.write('\n')
        f.write('    dut._log.info("Waiting for some rising edges on all clock signals")\n')
        for port_ in clock_ports:
            f.write('    yield ClockCycles(dut.%s, 3)\n' % (port_._name))
            f.write('    yield RisingEdge(dut.%s)\n' % (port_._name))
        if len(clock_ports) == 0:
            f.write('    dut._log.info("    <none>")\n')

        f.write('\n')
        f.write('    dut._log.info("Reading all DUT outputs")\n')
        f.write('    # other possibilities: output._name.value or int(output._name)\n')  # FIXME

        maxlen = get_name_maxlen(output_ports)
        for port_ in output_ports:
            f.write('    %s = dut.%s.value.binstr\n' % ((port_._name+'_val').ljust(maxlen+len('_val')), port_._name))
        for port_ in output_ports:
            f.write("""    dut._log.info("%s = %%s" %% str(%s))\n""" % ((port_._name+'_val').ljust(maxlen+len('_val')), (port_._name+'_val')))
        if len(output_ports) == 0:
            f.write('    dut._log.info("    <none>")\n')
        
        f.write('''
    dut._log.info("Waiting 10 ns...")
    yield Timer(10, units='ns')
    dut._log.info("Waiting 10 ns...done")\n''')

    dut._log.warning('Wrote testbench template %s' % (filename))    
    dut._log.warning('Try running with\n    make %s MODULE=testbench_template' % (os.getenv("MAKEFLAGS")[5:]))
