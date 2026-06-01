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

.. module:: cocotb_tools._pytest.plugin

.. autofixture:: dut

.. autofixture:: hdl_session

.. autofixture:: hdl


.. _api-pytest-plugin-markers:

Markers
=======

.. module:: cocotb_tools._pytest.mark

.. autodecorator:: cocotb_runner

.. autodecorator:: cocotb_test

.. autodecorator:: cocotb_timeout

.. autodecorator:: cocotb_library

.. autodecorator:: cocotb_sources

.. autodecorator:: cocotb_defines

.. autodecorator:: cocotb_includes

.. autodecorator:: cocotb_parameters

.. autodecorator:: cocotb_plusargs

.. autodecorator:: cocotb_env

.. autodecorator:: cocotb_seed

.. autodecorator:: cocotb_timescale

.. autodecorator:: cocotb_always

.. autodecorator:: cocotb_clean

.. autodecorator:: cocotb_waves

.. autodecorator:: cocotb_build_args

.. autodecorator:: cocotb_elab_args

.. autodecorator:: cocotb_test_args

.. autodecorator:: cocotb_pre_cmd


.. _api-pytest-plugin-hdl:

HDL Fixture Request
===================

.. module:: cocotb_tools._pytest.hdl

.. autoclass:: HDL
    :members:


.. _api-pytest-plugin-hook-specs:

Hook Specifications
===================

.. module:: cocotb_tools._pytest.hookspecs

.. autofunction:: pytest_cocotb_make_hdl

.. autofunction:: pytest_cocotb_make_runner
