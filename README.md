**cocotb** is a coroutine based cosimulation library for writing VHDL and Verilog testbenches in Python.

[![Documentation Status](https://readthedocs.org/projects/cocotb/badge/?version=latest)](https://docs.cocotb.org/en/latest/)
[![Build Status](https://travis-ci.org/cocotb/cocotb.svg?branch=master)](https://travis-ci.org/cocotb/cocotb)
[![PyPI](https://img.shields.io/pypi/dm/cocotb.svg?label=PyPI%20downloads)](https://pypi.org/project/cocotb/)
[![Gitpod Ready-to-Code](https://img.shields.io/badge/Gitpod-ready--to--code-blue?logo=gitpod)](https://gitpod.io/#https://github.com/cocotb/cocotb)
[![codecov](https://codecov.io/gh/cocotb/cocotb/branch/master/graph/badge.svg)](https://codecov.io/gh/cocotb/cocotb)

* Read the [documentation](https://docs.cocotb.org)
* Get involved:
  * [Raise a bug / request an enhancement](https://github.com/cocotb/cocotb/issues/new) (Requires a GitHub account)
  * [Join the mailing list](https://lists.librecores.org/listinfo/cocotb)
  * [Join the Gitter chat room](https://gitter.im/cocotb)

## Installation

Cocotb requires:

- Python 3.5+
- A C++11 compiler
- An HDL simulator (such as [Icarus Verilog](http://iverilog.icarus.com/))

After installing these dependencies, the latest stable version of cocotb can be installed with pip.

```command
pip install cocotb
```

**!!! Windows Users !!!** See [here](https://docs.cocotb.org/en/stable/install.html) for installation instructions.

For more details on installation, including prerequisites, see [the documentation](https://docs.cocotb.org/en/stable/install.html).

For detail on how to install the *development* version of cocotb, see [the lastest documentation](https://docs.cocotb.org/en/latest/install_devel.html#install-devel).

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
from cocotb.triggers import FallingEdge

@cocotb.test()
async def test_dff_simple(dut):
    """ Test that d propagates to q """

    clock = Clock(dut.clk, 10, units="us")  # Create a 10us period clock on port clk
    cocotb.fork(clock.start())  # Start the clock

    for i in range(10):
        val = random.randint(0, 1)
        dut.d <= val  # Assign the random value val to the input port d
        await FallingEdge(dut.clk)
        assert dut.q == val, "output q was incorrect on the {}th cycle".format(i)
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

For more information please see the [cocotb documentation](https://docs.cocotb.org/) and the [wiki](https://github.com/cocotb/cocotb/wiki).

## Tutorials, examples and related projects

* [Endian Swapper tutorial](https://docs.cocotb.org/en/stable/endian_swapper.html)
* [Ping using TUN/TAP tutorial](https://docs.cocotb.org/en/stable/ping_tun_tap.html)
* [Cocotb based USB 1.1 test suite for FPGA IP, with testbenches for a variety of open source USB cores](https://github.com/antmicro/usb-test-suite-build)
* [Functional Coverage and Constrained Randomization Extensions for Cocotb](https://github.com/mciepluc/cocotb-coverage)
* [UVM 1.2 port to Python](https://github.com/tpoikela/uvm-python)

For more related resources please check the [wiki](https://github.com/cocotb/cocotb/wiki/Further-Resources) and the [list of projects depending on cocotb](https://github.com/cocotb/cocotb/network/dependents).
