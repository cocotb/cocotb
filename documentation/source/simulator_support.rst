#################
Simulator Support
#################

This page documents any known quirks and gotchas in the various simulators.

Icarus
------

Accessing bits of a vector doesn't work:

.. code-block:: python

    dut.stream_in_data[2] <= 1

See "access_single_bit" test in examples/functionality/tests/test_discovery.py.


Synopsys VCS
------------

Aldec Riviera-PRO
-----------------

Mentor Questa
-------------

Mentor Modelsim
---------------
Any ModelSim-PE or ModelSim-PE derivative (like ModelSim Microsemi, Altera, Lattice Edition) does not support the VHDL FLI feature.
If you try to run with FLI enabled, you will see a vsim-FLI-3155 error:

.. code-block:: bash

    ** Error (suppressible): (vsim-FLI-3155) The FLI is not enabled in this version of ModelSim.

ModelSim DE and SE (and Questa, of course) supports the FLI.

Cadence Incisive
----------------

GHDL
----
