
**cocotb** is a coroutine based cosimulation library for writing VHDL and Verilog testbenches in Python.

TODO
====

 - [ ] Block align log messages that span multiple lines
 - [ ] Common functions for dumping a diff, nicely coloured (see scapy.utils.hexdiff)


Rationale
=========
VHDL and Verilog are both unsuitable for writing complex testbenches. eRM, SystemVerilog and the various SV based methodologies have emerged to address this deficiency. These verification methodologies are large and cumbersome, requiring specialist knowledge, significant time investment and expensive toolchains to achieve satisfactory verification. The overhead of setting up testbenches is onerous so often designers write small throwaway testbenches at a block level and defer the majority of verification to a large system level testbench. Cocotb intends to bridge this gap in order to make block-level testing useful, reusable, fast, accessible to a much wider skill-set. The net effect is that bugs will be discovered earlier in the design cycle which equates to significant time and cost saving.


Overview
========


A typical cocotb testbench requires no additional RTL code. The Design Under Test (DUT) is instantiated as the toplevel in the simulator without any wrapper code. Cocotb drives stimulus onto the inputs to the DUT (or further down the hierarchy) and monitors the outputs directly from Python.

Cocotb comprises 3 layers:

### GPI (Generic Procedural Interface)

This layer abstracts the simulator language interface to provide a common set of functionality. Supports VHDL via VHPI and Verilog/SystemVerilog via VPI. Modelsim FLI may be supported in the future.

### simulatormodule

A CPython extension which utilises GPI to expose the simulator to Python.

### cocotb Python package

Python infrastructure including coroutine scheduler, base classes etc. The cocotb package provides a mechanism to traverse the hierarchy, query signal values, force signals to particular values and control simulator execution.

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

Advantages
==========
* Low overhead to creating testbenches to facilitate block-level verification
* Favourable learning curve compared to eRM/OVM/UVM
* Leverage existing Python and C libraries easily
* Multi-language (Verilog/VHDL) and cross multi-simulator compatible
* Supports directed and randomised testing


Disadvantages
=============
* Simulation is slower than native language testbench
* Non-standard


Similar projects
================

Several examples exist of projects providing a VPI interface into a language other than C and (most notably http://pyhvl.sourceforge.net/ and http://snk.tuxfamily.org/lib/ruby-vpi/). MyHDL (http://www.myhdl.org/) seeks to displace VHDL and Verilog with a Python framework that can generate synthesiable RTL.
