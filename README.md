**cocotb** is a coroutine based cosimulation library for writing VHDL and Verilog testbenches in Python.

[![Documentation Status](https://readthedocs.org/projects/cocotb/badge/?version=latest)](https://docs.cocotb.org/en/latest/)
[![CI](https://github.com/cocotb/cocotb/actions/workflows/build-test-dev.yml/badge.svg?branch=master)](https://github.com/cocotb/cocotb/actions/workflows/build-test-dev.yml)
[![PyPI](https://img.shields.io/pypi/dm/cocotb.svg?label=PyPI%20downloads)](https://pypi.org/project/cocotb/)
[![Gitpod Ready-to-Code](https://img.shields.io/badge/Gitpod-ready--to--code-blue?logo=gitpod)](https://gitpod.io/#https://github.com/cocotb/cocotb)
[![codecov](https://codecov.io/gh/cocotb/cocotb/branch/master/graph/badge.svg)](https://codecov.io/gh/cocotb/cocotb)

* Read the [documentation](https://docs.cocotb.org)
* Get involved:
  * [Raise a bug / request an enhancement](https://github.com/cocotb/cocotb/issues/new) (Requires a GitHub account)
  * [Join the Gitter chat room](https://gitter.im/cocotb/Lobby)

**Note: The current `master` branch of the cocotb repository is expected to be released as cocotb 2.0, which contains API-breaking changes from previous 1.x releases. Please use the `stable/1.8` branch if you're building cocotb from source, or just [install it from PyPi](https://pypi.org/project/cocotb/).**

## Installation

The current stable version of cocotb requires:

- Python 3.6+
- GNU Make 3+
- An HDL simulator (such as [Icarus Verilog](https://docs.cocotb.org/en/stable/simulator_support.html#icarus-verilog),
[Verilator](https://docs.cocotb.org/en/stable/simulator_support.html#verilator),
[GHDL](https://docs.cocotb.org/en/stable/simulator_support.html#ghdl) or
[other simulator](https://docs.cocotb.org/en/stable/simulator_support.html))

After installing these dependencies, the latest stable version of cocotb can be installed with pip.

```command
pip install cocotb
```

For more details on installation, including prerequisites,
see [the documentation](https://docs.cocotb.org/en/stable/install.html).

For details on how to install the *development* version of cocotb,
see [the preliminary documentation of the future release](https://docs.cocotb.org/en/latest/install_devel.html#install-devel).

## Usage

As a first trivial introduction to cocotb, the following example "tests" a flip-flop.

First, we need a hardware design which we can test. For this example, create a file `dff.sv` with SystemVerilog code for a simple [D flip-flop](https://en.wikipedia.org/wiki/Flip-flop_(electronics)#D_flip-flop). You could also use any other language a [cocotb-supported simulator](https://docs.cocotb.org/en/stable/simulator_support.html) understands, e.g. VHDL.

```systemverilog
// dff.sv

`timescale 1us/1ns

module dff (
    output logic q,
    input logic clk, d
);

always @(posedge clk) begin
    q <= d;
end

endmodule
```

An example of a simple randomized cocotb testbench:

```python
# test_dff.py
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ReadOnly, RisingEdge

@cocotb.test
async def dff_simple_test(dut):
    """Test that d propagates to q"""

    # Set initial input value to prevent it from floating
    dut.d.value = 0

    clock = Clock(dut.clk, 10, units="us")  # Create a 10us period clock on port clk
    # Start the clock. Start it low to avoid issues on the first RisingEdge
    cocotb.start_soon(clock.start(start_high=False))

    # generate stimulus
    stimulus = [random.randint(0, 1) for _ in range(10)]

    # calculated expected outputs
    expecteds = [val for val in stimulus]

    async def drive_input():
        for val in stimulus:
            await RisingEdge(dut.clk)  # Synchronize with clock before driving.
            dut.d.value = val  # Assign the stimulus value to the input port 'd'.

    # Run the driver coroutine concurrently to the monitoring and checking logic below.
    cocotb.start_soon(drive_input())

    # Wait 1 clock cycle for input to propagate to output.
    await RisingEdge(dut.clk)

    for expected_val in expecteds:
        await RisingEdge(dut.clk)  # Synchronize with clock, then...
        await ReadOnly()  # Wait for all signal changes to settle.
        assert (
            dut.q.value == expected_val
        )  # Check the actual output against the expected.
```

A simple Makefile:

```make
# Makefile

TOPLEVEL_LANG = verilog
VERILOG_SOURCES = $(shell pwd)/dff.sv
TOPLEVEL = dff
MODULE = test_dff

include $(shell cocotb-config --makefiles)/Makefile.sim
```

In order to run the test with Icarus Verilog, execute:

```command
make SIM=icarus
```

[![asciicast](https://asciinema.org/a/317220.svg)](https://asciinema.org/a/317220)

For more information please see the [cocotb documentation](https://docs.cocotb.org/)
and [our wiki](https://github.com/cocotb/cocotb/wiki).

## Tutorials, examples and related projects

* the tutorial section [in the official documentation](https://docs.cocotb.org/)
* [cocotb-bus](https://github.com/cocotb/cocotb-bus) for pre-packaged testbenching tools and reusable bus interfaces.
* [cocotb-based USB 1.1 test suite](https://github.com/antmicro/usb-test-suite-build) for FPGA IP, with testbenches for a variety of open source USB cores
* [`cocotb-coverage`](https://github.com/mciepluc/cocotb-coverage), an extension for Functional Coverage and Constrained Randomization
* [`uvm-python`](https://github.com/tpoikela/uvm-python), an almost 1:1 port of UVM 1.2 to Python
* our wiki [on extension modules](https://github.com/cocotb/cocotb/wiki/Further-Resources#extension-modules-cocotbext)
* the list of [GitHub projects depending on cocotb](https://github.com/cocotb/cocotb/network/dependents)
