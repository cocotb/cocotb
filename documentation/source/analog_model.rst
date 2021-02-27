#########################
Models of Analog Circuits
#########################

.. versionadded:: 2.0

This is the example :mod:`analog_model` showing how to use Python models
for analog circuits together with a digital part.
For an FPGA, these analog circuits would be implemented off-chip,
while for an ASIC, they would usually co-exist with the digital part on the same die.

The Python model consists of an Analog Front-End (AFE) in file :file:`afe.py` containing
a Programmable Gain Amplifier (PGA) with a selectable gain of ``5.0`` and ``10.0``,
and a 13-bit Analog-to-Digital Converter (ADC) with a reference voltage of ``2.0 V``.
These analog models hand over data via a blocking :class:`cocotb.queue.Queue`.

The digital part (in :file:`digital.sv`)
monitors the measurement value converted by the ADC
and selects the gain of the PGA based on the received value.

A test :file:`test_analog_model.py` exercises these submodules.

When running the example, you will get the following output:

.. code-block:: none

        0.00ns INFO     ...test_analog_model.0x7ff913700490       decorators.py:313  in _advance                        Starting test: "test_analog_model"
                                                                                                                        Description: Exercise an Analog Front-end and its digital controller.
     1001.00ns INFO     cocotb.digital                     test_analog_model.py:55   in test_analog_model               AFE converted input value 0.1V to 2047
     3000.00ns (digital) HDL got meas_val=2047 (0x07ff)
     3000.00ns (digital) PGA gain select was 0 --> calculated AFE input value back to 0.099963
     3000.00ns (digital) Measurement value is less than 30% of max, switching PGA gain from 5.0 to 10.0
     7301.00ns INFO     cocotb.digital                     test_analog_model.py:55   in test_analog_model               AFE converted input value 0.1V to 4095
     9000.00ns (digital) HDL got meas_val=4095 (0x0fff)
     9000.00ns (digital) PGA gain select was 1 --> calculated AFE input value back to 0.099988
    13301.00ns INFO     cocotb.digital                     test_analog_model.py:55   in test_analog_model               AFE converted input value 0.0V to 0
    15000.00ns (digital) HDL got meas_val=0 (0x0000)
    15000.00ns (digital) PGA gain select was 1 --> calculated AFE input value back to 0.000000
   Saturating measurement value 10238 to [0:8191]!
    19301.00ns INFO     cocotb.digital                     test_analog_model.py:55   in test_analog_model               AFE converted input value 0.25V to 8191
    21000.00ns (digital) HDL got meas_val=8191 (0x1fff)
    21000.00ns (digital) PGA gain select was 1 --> calculated AFE input value back to 0.200000
    21000.00ns (digital) Measurement value is more than 70% of max, switching PGA gain from 10.0 to 5.0
    25301.00ns INFO     cocotb.digital                     test_analog_model.py:55   in test_analog_model               AFE converted input value 0.25V to 5119
    27000.00ns (digital) HDL got meas_val=5119 (0x13ff)
    27000.00ns (digital) PGA gain select was 0 --> calculated AFE input value back to 0.249982
    30301.00ns INFO     cocotb.regression                         regression.py:364  in _score_test                     Test Passed: test_analog_model


You can view the source code of the example by clicking the file names below.

.. details:: :file:`afe.py`

   .. literalinclude:: ../../examples/analog_model/afe.py
      :language: python

.. details:: :file:`digital.sv`

   .. literalinclude:: ../../examples/analog_model/digital.sv
      :language: systemverilog

.. details:: :file:`test_analog_model.py`

   .. literalinclude:: ../../examples/analog_model/test_analog_model.py
      :language: python

.. details:: :file:`Makefile`

   .. literalinclude:: ../../examples/analog_model/Makefile
      :language: make
