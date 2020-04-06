**Your input is needed!** Please help out by taking 10 minutes to fill out this year's cocotb user survey. This survey gives the development community important feedback to steer the future of cocotb into the right direction for your use case.
[**Take the cocotb user survey now**](https://docs.google.com/forms/d/e/1FAIpQLSfD36PldzszbuZjysss3AMvxkf6XCtSbDTVh9qVNNYDaHTZ_w/viewform).

---

**cocotb** is a coroutine based cosimulation library for writing VHDL and Verilog testbenches in Python.

[![Documentation Status](https://readthedocs.org/projects/cocotb/badge/?version=latest)](https://docs.cocotb.org/en/latest/)
[![Build Status](https://travis-ci.org/cocotb/cocotb.svg?branch=master)](https://travis-ci.org/cocotb/cocotb)
[![PyPI](https://img.shields.io/pypi/dm/cocotb.svg?label=PyPI%20downloads)](https://pypi.org/project/cocotb/)

* Read the [documentation](https://docs.cocotb.org)
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

* [Endian Swapper tutorial](https://docs.cocotb.org/en/latest/endian_swapper.html)
* [Ping using TUN/TAP tutorial](https://docs.cocotb.org/en/latest/ping_tun_tap.html)
* [OpenCores JPEG Encoder example](https://github.com/chiggs/oc_jpegencode/)
