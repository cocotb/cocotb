
**cocotb** is a coroutine based cosimulation library for writing VHDL and Verilog testbenches in Python.

Overview
========

VHDL and Verilog are both unsuitable for writing complex testbenches. eRM, SystemVerilog and the various SV based methodologies have emerged to address this deficiency. These verification methodologies are large and cumbersome, requiring specialist knowledge, significant time investment and expensive toolchains to achieve satisfactory verification. The overhead of setting up testbenches is onerous so often designers write small throwaway testbenches at a block level and defer the majority of verification to a large system level testbench.

Cocotb intends to bridge this gap in order to make block-level testing useful, reusable, fast, accessible to a much wider skill-set. The net effect is that bugs will be discovered earlier in the design cycle which equates to significant time and cost saving.

Why verify in Python?
=====================

* It's **easy** to interface to other languages from Python
* Python has a huge library of existing code to **re-use** like [constraint solvers](https://code.google.com/p/or-tools/) [packet parsing/generation](http://www.secdev.org/projects/scapy/) libraries.
* Python is **interpreted**. Tests can be edited and re-run them without having to recompile the design or even exit the simulator GUI.
* Writing Python is **fast**, it's *easy to understand* and *everybody* knows it.



Useful links
============

* Read the [documentation](http://cocotb.readthedocs.org)
* Get involved: [Raise a bug / request an enhancement](https://github.com/potentialventures/cocotb/issues/new) (Requires a GitHub account)
* Get in contact: [E-mail us](mailto:cocotb@potentialventures.com)


Example
=======

A simplistic example of generating a clock with 10ns period:
```python
@cocotb.coroutine
def clock(signal):
    while True:
        signal <= 1
        yield Timer(5)
        signal <= 0
        yield Timer(5)
```

The python "yield" keyword is used to suspend the coroutine and return control back to the simulator until a condition is met. In this case, the condition is a simple timer that fires after 5ns of simulation time.

This may seem pretty pointless, in fact a Verilog process to perform the same operation requires fewer lines of code. Let's examine a more useful example:

```python
@cocotb.coroutine
def pcap_replay(bus, filename):
    prevtime = 0
    for timestamp, packet in dpkt.pcap.Reader(open(filename, 'r')):
        yield Timer((timestamp - prevtime) * 1000)
        yield bus.send(packet)
```

Here we utilise a thirdparty python library called dpkt to iterate over packets in a PCAP packet capture. This becomes trivially easy in Python when compared to a VHDL/Verilog/SystemVerilog implementation. The argument "bus" is an instance of a Driver class which provides a send method to serialise the packet transaction over multiple cycles on the bus. Although the majority of the complexity is hidden in this (reusable) Driver class the actual implementation is once again straightforward:

```python
def send(self, packet):

    words = len(packet) / (len(self.data) / 8)

    yield RisingEdge(self.clk)            # Synchronise to bus clock
    self.sop <= 1                         # First word is start-of-packet
    self.valid <= 1

    for index, word in enumerate(packet):
        self.data <= word
        yield rising_edge(self.clk)        
        self.sop <= 0
        if index == words - 1:
            self.eop <= 1
            self.len <= len(word)

    yield rising_edge(self.clk)
    self.eop <= 0
    self.valid <= 0
```

Similar projects
================

[MyHDL](http://www.myhdl.org/) seeks to displace VHDL and Verilog with a Python framework that can generate synthesiable RTL.

Several examples exist of projects providing a VPI interface into a language other than C:

* [PyHVL](http://pyhvl.sourceforge.net/)
* [Ruby-vpi](http://snk.tuxfamily.org/lib/ruby-vpi/)

Cocotb tries to build on the advances made by these projects while learning from the direction of UVM and other verification standards.

