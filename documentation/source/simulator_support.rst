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

Cadence Incisive
----------------

