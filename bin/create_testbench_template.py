import cocotb
from cocotb.triggers import Timer
from cocotb.result import TestError, TestFailure
from cocotb.handle import *

import logging
import pprint

# FIXME: port stuff needs SINGLETON_HANDLES in lib/gpi/Makefile not set!


def get_longest_name(objlist):
    '''
    Return the longest name of a list of objects.
    '''
    return max(len(x._name) for x in objlist)


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
            dut._log.info(f'{thing_._port_direction_string[4:].capitalize()} Port {thing_._path}')
            if thing_._port_direction_string == 'GPI_INPUT':
                input_ports.append(thing_)
            elif thing_._port_direction_string == 'GPI_OUTPUT':
                output_ports.append(thing_)
            elif thing_._port_direction_string == 'GPI_INOUT':
                inout_ports.append(thing_)
                input_ports.append(thing_)
                output_ports.append(thing_)
            else:
                dut._log.warning(f'Unhandled port direction {thing_._port_direction_string} of {thing_._path}!')

    # match names to identify "special" ports:
    for port_ in input_ports+inout_ports:
        if port_._name.startswith('vd') or port_._name.startswith('vc'):
            # Examples: vdd, vddd, vdda, vdio, vcc, vcore
            dut._log.warning(f'Identified a supply port: {port_._name}')
            supply_ports.append(port_)
        elif port_._name.startswith('vs') or port_._name.startswith('gnd') or port_._name.endswith('gnd'):
            # Examples: gnd, agnd, dgnd, vs, vss, vssd, vsio
            dut._log.warning(f'Identified a ground port: {port_._name}')
            ground_ports.append(port_)
        elif (port_._name.startswith('clk') or port_._name.endswith('clk')
              or port_._name.startswith('clock') or port_._name.endswith('clock')):
            # Examples: clk_2MHz, clk_main, main_clk, main_clock
            dut._log.warning(f'Identified a clock: {port_._name}')
            clock_ports.append(port_)
        elif port_._name in ('reset', 'reset_n', 'rst', 'rst_n'):
            # Examples: exactly these
            dut._log.warning(f'Identified a reset: {port_._name}')
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
            f.write(f'''    dut.{port_._name} <= 0
    yield Timer(RESET_DURATION_NS, units='ns')
    dut.{port_._name} <= 1\n''')
        if len(reset_ports) == 0:
            f.write(f'    dut._log.info("    <none>")\n')
            
        f.write('\n')
        f.write('    dut._log.info("Setting identified supply ports")\n')
        for port_ in supply_ports:
            f.write(f'    dut.{port_._name} <= 1\n')
        if len(supply_ports) == 0:
            f.write('    dut._log.info("    <none>")\n')
            
        f.write('\n')
        f.write('    dut._log.info("Setting identified ground ports")\n')
        for port_ in ground_ports:
            f.write(f'    dut.{port_._name} <= 0\n')
        if len(ground_ports) == 0:
            f.write('    dut._log.info("    <none>")\n')

        f.write('\n')
        f.write('    dut._log.info("Starting identified clock(s)")\n')
        for port_ in clock_ports:
            f.write(f"    cocotb.fork(Clock(dut.{port_._name}, CLOCK_PERIOD_NS, units='ns').start())\n")
        if len(clock_ports) == 0:
            f.write('    dut._log.info("    <none>")\n')

        f.write('\n')
        f.write('    dut._log.info("Driving all remaining DUT inputs/inouts")\n')
        f.write('    # Changes needed for real signals (drive with "0.0"), and struct/record ports\n')
        remaining_ports = list(set(input_ports+inout_ports) -
                               set(supply_ports+ground_ports+clock_ports+reset_ports))
        for port_ in remaining_ports:
            f.write('    dut.{} <= 0x0\n'.format(port_._name.ljust(get_longest_name(remaining_ports))))
        if len(remaining_ports) == 0:
            f.write('    dut._log.info("    <none>")\n')
        
        f.write('\n')
        f.write('    dut._log.info("Waiting for some rising edges on all clock signals")\n')
        for port_ in clock_ports:
            f.write(f'    yield ClockCycles(dut.{port_._name}, 3)\n')
            f.write(f'    yield RisingEdge(dut.{port_._name})\n')
        if len(clock_ports) == 0:
            f.write('    dut._log.info("    <none>")\n')

        f.write('\n')
        f.write('    dut._log.info("Reading all DUT outputs")\n')
        f.write('    # other possibilities: output._name.value or int(output._name)\n')

        for port_ in output_ports:
            f.write('    dut._log.info("dut.{name_ljust} = {{val}}".format(val=dut.{name}.value.binstr))\n'.format(
                name_ljust=port_._name.ljust(get_longest_name(output_ports)), name=port_._name))
        if len(output_ports) == 0:
            f.write('    dut._log.info("    <none>")\n')
        
        f.write('''
    dut._log.info("Waiting 10 ns...")
    yield Timer(10, units='ns')
    dut._log.info("Waiting 10 ns...done")\n''')

    dut._log.info(f'Wrote testbench template {filename}')    
