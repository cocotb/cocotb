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

**!!! Bus and Testbenching Components !!!**
The reusable bus interfaces and testbenching components have recently been moved to the [cocotb-bus](https://github.com/cocotb/cocotb-bus) package.
You can easily install these at the same time as cocotb by adding the `bus` extra install: `pip install cocotb[bus]`.

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
from cocotb.triggers import RisingEdge
from cocotb.types import LogicArray

@cocotb.test()
async def dff_simple_test(dut):
    """Test that d propagates to q"""

    # Assert initial output is unknown
    assert LogicArray(dut.q.value) == LogicArray("X")
    # Set initial input value to prevent it from floating
    dut.d.value = 0

    clock = Clock(dut.clk, 10, units="us")  # Create a 10us period clock on port clk
    # Start the clock. Start it low to avoid issues on the first RisingEdge
    cocotb.start_soon(clock.start(start_high=False))

    # Synchronize with the clock. This will regisiter the initial `d` value
    await RisingEdge(dut.clk)
    expected_val = 0  # Matches initial input value
    for i in range(10):
        val = random.randint(0, 1)
        dut.d.value = val  # Assign the random value val to the input port d
        await RisingEdge(dut.clk)
        assert dut.q.value == expected_val, f"output q was incorrect on the {i}th cycle"
        expected_val = val # Save random value for next RisingEdge

    # Check the final input on the next clock
    await RisingEdge(dut.clk)
    assert dut.q.value == expected_val, "output q was incorrect on the last cycle"
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

## Setup for development
```
echo 'export PYTHONPATH="${PYTHONPATH}:<path to your cocotb fork>"' >> ~/.bash_profile
sudo dnf install libstdc++-static ghdl
git clone ...
cd cocotb/
sudo pip install pytest
sudo pip install -e .
```

## Work in progress:
- Removing `from cocotb.binary` in cocotb/handle.py:40 (replace with types/logic_array.py)
- Trying `cd tests/test_cases/test_select_testcase && make`
