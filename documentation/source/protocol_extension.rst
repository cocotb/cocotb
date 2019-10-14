How to write a protocol extension
=================================

Cocotb take care of the core communication between the simulator and testbench.
To use some known busses like wishbone, avalon, spi, i2c,... An extension is required.

This is a guideline that will explain how to write a python module protocol
extension for cocotb.

Naming convention
-----------------

A cocotb extension module must begin by `cocotb_` and terminate with protocol
name.

For exemple, with spi the module extension is `cocotb_spi`.

Bus driver
----------

A Bus driver is a python class that factorize common behavior and check for
presence of some signals.

A Bus driver is an active class that be driven in the main testbench. Example is
given with avalon bus in `cocotb/drivers/avalon.py`.

With AvalonMaster class we can generate stimulis for reading and writing on bus.

The main class is named `BusDriver` and is defined in `cocotb/drivers/__init__.py`

TODO: give an example.

Bus Monitor
-----------

A Bus monitor is mainly a passive class that will monitor the bus.

TODO: explain monitor

Python module
-------------

The module file hierarchy should be as following ::

  ├── cocotb_spi/
  │   └── __init__.py
  ├── README.md
  └── setup.py

With python module source code in directory cocotb_spi and module configuration
in setup.py

setup.py is a python configuration file that be used for packaging. An example
is given above ::

  from setuptools import setup

  setup(name='cocotb_spi',
        version='0.1',
        py_modules=['cocotb_spi'],
        install_requires=['cocotb'],
        classifiers=[
          "Programming Language :: Python :: 3",
          "License :: OSI Approved :: MIT License",
          "Operating System :: OS Independent",
          "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)"])

With this config file, python module can be installed with::

  $ python -m pip install cocotb_spi

or for development (in package directory)::

  $ python -m pip install -e .

Then module can be imported with import keyword in your testbench ::

  import cocotb_spi

Documentation
-------------

How to write documentation for the module correctly.

Distribution
------------

Cocotb official package is hosted on github :
https://github.com/cocotb

Ask maintainer to host your module repository in it.
