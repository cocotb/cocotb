.. _junit:

*****************
JUnit Test Report
*****************

Every time a cocotb regression finishes, a JUnit XML test report file is generated that contains the results of the executed tests.
The format of this file is described in :ref:`junit-reference`.

Changing File Output Location
=============================

By default the results are written to a file called ``results.xml``,
but can be overridden by setting the environment variable :envvar:`COCOTB_RESULTS_FILE`.

Makefiles and cocotb Runner
---------------------------

Use the :envvar:`COCOTB_RESULTS_FILE` environment variable to specify the output file name when invoking ``make`` or the cocotb Runner.

.. code:: shell

    COCOTB_RESULTS_FILE=junit.xml make

pytest Plugin
-------------

Use the ``--junit-xml`` command line option to specify the output file name when invoking ``pytest``.

.. code:: shell

    pytest --junit-xml=junit.xml

.. _junit-attachments:

Adding Attachments
==================

It is possible to include file attachments like simulation logs or waveform files in the generated results file.
The file contents are not included directly in the results file,
but are included as file links which certain CI tools like Jenkins xUnit plugin will interpret, upload, and provide to the user as hyperlinks to the uploaded files.

Makefiles and cocotb Runner
---------------------------

The :envvar:`COCOTB_RESULTS_ATTACHMENTS` environment variable is a comma-separated list of files to attach.

.. code:: shell

    COCOTB_RESULTS_ATTACHMENTS=sim.log,sim_build/waveform.vcd make

pytest Plugin
-------------

Setting the ``junit_logging`` pytest INI config option to ``system-out`` or ``all`` is required for attachments to be added when using the pytest plugin.

.. TODO Why does this work?

.. code:: shell

    pytest --override-ini=junit_logging=system-out --junit-xml=junit.xml ...


.. _junit-paths:

Outputting Relative Paths
=========================

The :envvar:`COCOTB_RESULTS_RELATIVE_TO` environment variable can be used to convert all absolute paths reported in the generated XML file to relative ones, including XML attributes, properties and text.

Makefiles and cocotb Runner
---------------------------

This functionality is not enabled by default when using the Makefiles or cocotb Runners.
It must be explicitly enabled by setting the :envvar:`COCOTB_RESULTS_RELATIVE_TO` environment variable.
A reasonable default is the directory from which the Makefile or cocotb Runner is invoked.

.. code:: shell

    COCOTB_RESULTS_RELATIVE_TO=$(pwd) make

Alternatively, it can be set relative to the Makefile location.

.. code:: shell

    MAKEFILE_DIR = $(dirname $(realpath $(lastword $(MAKEFILE_LIST))))
    COCOTB_RESULTS_RELATIVE_TO=$(MAKEFILE_DIR) make

pytest Plugin
-------------

When using the :ref:`pytest-support`, the path hint used to convert absolute paths to relative ones is determined from where the ``pytest`` command was invoked.
Use the :envvar:`COCOTB_RESULTS_RELATIVE_TO` environment variable when invoking pytest to override that.

.. code:: shell

    COCOTB_RESULTS_RELATIVE_TO=$(pwd)/cocotb_subproject pytest --junit-xml=junit.xml ...
