**cocotb** is a coroutine based cosimulation library for writing VHDL and Verilog testbenches in Python.

[![Documentation Status](https://readthedocs.org/projects/cocotb/badge/?version=latest)](http://cocotb.readthedocs.org/en/latest/)
[![Build Status](https://travis-ci.org/potentialventures/cocotb.svg?branch=master)](https://travis-ci.org/potentialventures/cocotb)
[![Coverity Scan Status](https://scan.coverity.com/projects/6110/badge.svg)](https://scan.coverity.com/projects/cocotb)

* Read the [documentation](http://cocotb.readthedocs.org)
* Get involved:
  * [Raise a bug / request an enhancement](https://github.com/potentialventures/cocotb/issues/new) (Requires a GitHub account)
  * [Join the mailing list](https://lists.librecores.org/listinfo/cocotb)
  * [Join the Gitter chat room](https://gitter.im/cocotb)
* Get in contact: [E-mail us](mailto:cocotb@potentialventures.com)
* Follow us on twitter: [@PVCocotb](https://twitter.com/PVCocotb)

## Quickstart

    # Install pre-requisites (waveform viewer optional)
    sudo yum install -y iverilog python-devel gtkwave
    
    # Checkout git repositories
    git clone https://github.com/potentialventures/cocotb.git
    
    # Run the tests...
    cd cocotb/examples/endian_swapper/tests
    make
    
    # View the waveform
    gtkwave waveform.vcd


## Tutorials and examples

* [Endian Swapper tutorial](https://cocotb.readthedocs.org/en/latest/endian_swapper.html)
* [Ping using TUN/TAP tutorial](https://cocotb.readthedocs.org/en/latest/ping_tun_tap.html)
* [OpenCores JPEG Encoder example](https://github.com/chiggs/oc_jpegencode/)
