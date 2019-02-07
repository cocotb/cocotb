#################
Simulator Support
#################

This page documents any known quirks and gotchas in the various simulators.

Icarus
------

Accessing bits of a vector doesn't work:

.. code-block:: python

    dut.stream_in_data[2] <= 1

See ``access_single_bit`` test in :file:`examples/functionality/tests/test_discovery.py`.


Synopsys VCS
------------

Aldec Riviera-PRO
-----------------
The ``$LICENSE_QUEUE`` environment variable can be used for this simulator – 
this setting will be mirrored in the TCL ``license_queue`` variable to control runtime license checkouts.

Mentor Questa
-------------

Mentor Modelsim
---------------

Any ModelSim PE or ModelSim PE derivative (like ModelSim Microsemi, Intel, Lattice Edition) does not support the VHDL FLI feature.
If you try to run with FLI enabled, you will see a ``vsim-FLI-3155`` error:

.. code-block:: bash

    ** Error (suppressible): (vsim-FLI-3155) The FLI is not enabled in this version of ModelSim.

ModelSim DE and SE (and Questa, of course) supports the FLI.

Some versions of Modelsim are still 32-bit. Using a tool such as Anaconda or building Python for a 32-bit architecture, it is possible to use that environment to work with cocotb. Some versions of Python have libraries compiled in a manner that don't work well with certain simulators. This requires further testing.

Cadence Incisive, Cadence Xcelium
---------------------------------

GHDL
----
Support is preliminary. 
