.. _api-pytest-plugin:

***********************
Pytest Plugin Reference
***********************

.. warning::
    The pytest plugin is under active development and the API **will** change in breaking ways over the next release or two.

    You can still use pytest with the :ref:`Python runners <runner-with-pytest>` for building designs and running simulations,
    and you can also still use pytest features in cocotb tests, such :func:`pytest.raises`, :func:`pytest.skip`, or pytest's assertion rewriting.


.. _api-pytest-plugin-fixtures:

Fixtures
========

.. module:: cocotb_tools.pytest.plugin

.. autofixture:: dut


.. _api-pytest-plugin-markers:

Markers
=======

.. module:: cocotb_tools.pytest.mark

.. autodecorator:: cocotb

.. autodecorator:: cocotb_simulation

.. autodecorator:: cocotb_test

.. autodecorator:: cocotb_suffix

.. autodecorator:: cocotb_simulator

.. autodecorator:: cocotb_test_modules

.. autodecorator:: cocotb_toplevel

.. autodecorator:: cocotb_toplevel_lang

.. autodecorator:: cocotb_toplevel_library

.. autodecorator:: cocotb_timeout

.. autodecorator:: cocotb_sources

.. autodecorator:: cocotb_defines

.. autodecorator:: cocotb_parameters

.. autodecorator:: cocotb_env

.. autodecorator:: cocotb_includes

.. autodecorator:: cocotb_plusargs

.. autodecorator:: cocotb_timescale

.. autodecorator:: cocotb_build_dir

.. autodecorator:: cocotb_build_args

.. autodecorator:: cocotb_elab_args

.. autodecorator:: cocotb_sim_args

.. autodecorator:: cocotb_pre_cmd

.. autodecorator:: cocotb_library

.. autodecorator:: cocotb_waves

.. autodecorator:: cocotb_verbose

.. autodecorator:: cocotb_always

.. autodecorator:: cocotb_clean

.. autodecorator:: cocotb_gui

.. autodecorator:: cocotb_gpi_interfaces

.. autodecorator:: cocotb_test_filter


.. _api-pytest-plugin-hdl:

Dut Fixture Request
===================

.. module:: cocotb_tools.pytest.dut

.. autoclass:: Dut
    :members:


.. _api-pytest-plugin-hook-specs:

Hook Specifications
===================

.. module:: cocotb_tools.pytest.hookspecs

.. autofunction:: pytest_cocotb_dut_create

.. autofunction:: pytest_cocotb_dut_run
