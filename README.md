**cocotb** is a coroutine based cosimulation library for writing VHDL and Verilog testbenches in Python.

[![Documentation Status](https://readthedocs.org/projects/cocotb/badge/?version=latest)](http://cocotb.readthedocs.org/en/latest/)
[![Build Status](https://travis-ci.org/cocotb/cocotb.svg?branch=master)](https://travis-ci.org/cocotb/cocotb)
[![PyPI](https://img.shields.io/pypi/dm/cocotb.svg?label=PyPI%20downloads)](https://pypi.org/project/cocotb/)

* Read the [documentation](http://cocotb.readthedocs.org)
* Get involved:
  * [Raise a bug / request an enhancement](https://github.com/cocotb/cocotb/issues/new) (Requires a GitHub account)
  * [Join the mailing list](https://lists.librecores.org/listinfo/cocotb)
  * [Join the Gitter chat room](https://gitter.im/cocotb)

## Installation

Cocotb can be installed by running `pip install cocotb`.

## Quickstart

    # Install pre-requisites (waveform viewer optional)
    sudo yum install -y iverilog python-devel gtkwave
    
    # Checkout git repositories
    git clone https://github.com/cocotb/cocotb.git
    
    # Install cocotb
    pip install ./cocotb
    
    # Run the tests...
    cd cocotb/examples/endian_swapper/tests
    make
    
    # View the waveform
    gtkwave waveform.vcd


## Tutorials and examples

* [Endian Swapper tutorial](https://cocotb.readthedocs.org/en/latest/endian_swapper.html)
* [Ping using TUN/TAP tutorial](https://cocotb.readthedocs.org/en/latest/ping_tun_tap.html)
* [OpenCores JPEG Encoder example](https://github.com/chiggs/oc_jpegencode/)
