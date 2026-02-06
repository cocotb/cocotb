.. _junit:

******************
JUnit Tests Report
******************

If you need to know what set of attributes are supported by the cocotb XML result file, see :ref:`junit-reference`.


.. _junit-attachments:

Attachments
===========

Makefiles and cocotb Runner
---------------------------

Simulation log and waveform files will be attached to generated JUnit XML file by using :ref:`junit-attributes-property` and :ref:`junit-attributes-system-out` XML elements.
The :envvar:`COCOTB_RESULTS_ATTACHMENTS` environment variable is used to define the list of attachments.

pytest Plugin
-------------

To include file attachments in :ref:`junit-attributes-system-out` XML element when generating JUnit XML file from pytest,
set the pytest ``junit_logging`` option to ``system-out`` or ``all``:

.. code:: shell

    pytest --override-ini=junit_logging=system-out --junit-xml=junit.xml ...


.. _junit-paths:

Paths
=====

Makefiles and cocotb Runner
---------------------------

The :envvar:`COCOTB_RESULTS_RELATIVE_TO` environment variable can be used to convert all absolute paths reported in
generated XML file to relative ones including XML attributes, properties and text.

Example:

.. code:: shell

    COCOTB_RESULTS_RELATIVE_TO="${CI_PROJECT_DIR:-$(pwd)}" pytest|make ...

pytest Plugin
-------------

When using the :ref:`pytest-support`, the path hint used to convert absolute paths to relative ones is determined
from where the ``pytest`` command was invoked. Use the :envvar:`COCOTB_RESULTS_RELATIVE_TO` environment variable to
override that.
