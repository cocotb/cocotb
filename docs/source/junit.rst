.. _junit:

*****************
JUnit Test Report
*****************

Every time a cocotb regression finishes, a JUnit XML test report file is generated that contains the results of the executed tests.
The format of this file is described in :ref:`junit-reference`.

Changing File Output Location
=============================

By default the results are written to a file called ``results.xml``,
but can be overridden by setting the :envvar:`COCOTB_RESULTS_FILE` environment variable
when invoking ``make`` or the cocotb Runner.

.. code:: shell

    COCOTB_RESULTS_FILE=junit.xml make

.. _junit-attachments:

Adding Attachments
==================

It is possible to include file attachments like simulation logs or waveform files in the generated results file.
The file contents are not included directly in the results file,
but are included as file links which certain CI tools like Jenkins xUnit plugin will interpret, upload, and provide to the user as hyperlinks to the uploaded files.

The :envvar:`COCOTB_RESULTS_ATTACHMENTS` environment variable is a comma-separated list of files to attach.

.. code:: shell

    COCOTB_RESULTS_ATTACHMENTS=sim.log,sim_build/waveform.vcd make


.. _junit-paths:

Outputting Relative Paths
=========================

The :envvar:`COCOTB_RESULTS_RELATIVE_TO` environment variable can be used to convert all absolute paths reported in the generated XML file to relative ones, including XML attributes, properties and text.

This functionality is not enabled by default when using the Makefiles or cocotb Runners.
It must be explicitly enabled by setting the :envvar:`COCOTB_RESULTS_RELATIVE_TO` environment variable.
A reasonable default is the directory from which the Makefile or cocotb Runner is invoked.

.. code:: shell

    COCOTB_RESULTS_RELATIVE_TO=$(pwd) make

Alternatively, it can be set relative to the Makefile location.

.. code:: shell

    MAKEFILE_DIR = $(dirname $(realpath $(lastword $(MAKEFILE_LIST))))
    COCOTB_RESULTS_RELATIVE_TO=$(MAKEFILE_DIR) make
