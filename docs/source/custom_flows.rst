.. _custom-flows:

******************************
Extending Existing Build Flows
******************************

In order to extend an existing build flow for use with cocotb,
this chapter shows the minimum settings to be done.

.. note::
   These instructions are an unsupported alternative to using the Makefiles provided by cocotb.
   The ``$(cocotb-config ...)`` syntax for executing ``cocotb-config`` works in the bash shell;
   adapt for your scripting language as needed.


For all simulators, the following environment variables need to be set:

* Define :envvar:`LIBPYTHON_LOC` using ``$(cocotb-config --libpython)``.
* Define :envvar:`PYGPI_PYTHON_BIN` using ``$(cocotb-config --python-bin)``.
* Define :envvar:`COCOTB_TEST_MODULES` with the name of the Python module(s) containing your testcases.

See the sections below for additional settings to be done, depending on the simulator.

.. _custom-flows-icarus:

Icarus Verilog
==============

* Call the ``vvp`` executable with the options
  ``-M $(cocotb-config --lib-dir) -m $(cocotb-config --lib-name vpi icarus)``.

Verilator
=========

* Extend the call to ``verilator`` with these options:

   .. code-block::

      --vpi --public-flat-rw --prefix Vtop \
      -LDFLAGS "-Wl,-rpath,$(cocotb-config --lib-dir) \
          -L$(cocotb-config --lib-dir) \
          -lcocotbvpi_verilator" \
      $(cocotb-config --share)/lib/verilator/verilator.cpp

* Run Verilator's makefile as follows: ``CPPFLAGS="-std=c++11" make -f Vtop.mk``

.. _custom-flows-vcs:

Synopsys VCS
============

* Create a file :file:`pli.tab` with the content ``acc+=rw,wn:*`` (or equivalent)
  to allow cocotb to access values in the design.
* Extend the ``vcs`` call with the options
  ``+vpi -P pli.tab -load $(cocotb-config --lib-name-path vpi vcs)``.

.. _custom-flows-aldec:
.. _custom-flows-riviera:

Aldec Riviera-PRO
=================

* The ``asim`` call needs the ``+access +w_nets`` option set to allow cocotb to access values in the design.

.. tab-set::

   .. tab-item:: Design with a VHDL Toplevel

      For a design with a VHDL toplevel, call ``asim`` with the option
      ``-loadvhpi $(cocotb-config --lib-name-path vhpi riviera):vhpi_startup_routines_bootstrap``.

      Set the :envvar:`GPI_EXTRA` environment variable to
      ``$(cocotb-config --lib-name-path vpi riviera):cocotbvpi_entry_point``
      if there are also (System)Verilog modules in the design.

   .. tab-item:: Design with a (System)Verilog Toplevel

      For a design with a (System)Verilog toplevel, call ``alog`` and ``asim`` with the option
      ``-pli $(cocotb-config --lib-name-path vpi riviera)``.

      Set the :envvar:`GPI_EXTRA` environment variable to
      ``$(cocotb-config --lib-name-path vhpi riviera):cocotbvhpi_entry_point``
      if there are also VHDL modules in the design.

.. _custom-flows-activehdl:

Aldec Active-HDL
================

* The ``asim`` call needs the ``+access +w_nets`` option set to allow cocotb to access values in the design.

.. tab-set::

   .. tab-item:: Design with a VHDL Toplevel

      For a design with a VHDL toplevel, call ``asim`` with the option
      ``-loadvhpi $(cocotb-config --lib-name-path vhpi activehdl):vhpi_startup_routines_bootstrap``.

      Set the :envvar:`GPI_EXTRA` environment variable to
      ``$(cocotb-config --lib-name-path vpi activehdl):cocotbvpi_entry_point``
      if there are also (System)Verilog modules in the design.

   .. tab-item:: Design with a (System)Verilog Toplevel

      For a design with a (System)Verilog toplevel, call ``alog`` and ``asim`` with the option
      ``-pli $(cocotb-config --lib-name-path vpi activehdl)``.

      Set the :envvar:`GPI_EXTRA` environment variable to
      ``$(cocotb-config --lib-name-path vhpi activehdl):cocotbvhpi_entry_point``
      if there are also VHDL modules in the design.

.. _custom-flows-siemens:

Mentor/Siemens EDA Questa and Modelsim
======================================

Questa supports two different flows: the traditional flow using ``vsim``, which is also used by ModelSim, and a modern alternative using ``qrun``.

.. tab-set::

   .. tab-item:: Design with a VHDL Toplevel

      For a design with a VHDL toplevel, call the ``vsim`` or ``qrun`` executable with the option
      ``-foreign "cocotb_init $(cocotb-config --lib-name-path fli questa)"``.

      Set the :envvar:`GPI_EXTRA` environment variable to
      ``$(cocotb-config --lib-name-path vpi questa):cocotbvpi_entry_point``
      if there are also (System)Verilog modules in the design.

   .. tab-item:: Design with a (System)Verilog Toplevel

      For a design with a (System)Verilog toplevel, call the ``vsim`` or ``qrun`` executable with the option
      ``-pli $(cocotb-config --lib-name-path vpi questa)``.

      Set the :envvar:`GPI_EXTRA` environment variable to
      ``$(cocotb-config --lib-name-path fli questa):cocotbfli_entry_point``
      if there are also VHDL modules in the design.

.. _custom-flows-cadence:

Cadence Incisive and Xcelium
============================

* The ``xrun`` call (or ``xmelab`` in multi-step mode) needs the ``-access +rwc``
  (or equivalent, e.g. :samp:`-afile {afile}`) option set to allow cocotb to access values in the design.

.. tab-set::

   .. tab-item:: Design with a VHDL Toplevel

      For a design with a VHDL toplevel, call the ``xrun`` or ``xmelab`` executable with the options
      ``-NEW_VHPI_PROPAGATE_DELAY -loadvpi $(cocotb-config --lib-name-path vpi xcelium):.vlog_startup_routines_bootstrap``.

      Set the :envvar:`GPI_EXTRA` environment variable to
      ``$(cocotb-config --lib-name-path vhpi xcelium):cocotbvhpi_entry_point``.
      This is because directly loading the VHPI library causes an error in Xcelium,
      so always load the VPI library and supply VHPI via ``GPI_EXTRA``.

   .. tab-item:: Design with a (System)Verilog Toplevel

      For a design with a (System)Verilog toplevel, call the ``xrun`` or ``xmelab`` executable with the option
      ``-loadvpi $(cocotb-config --lib-name-path vpi xcelium):.vlog_startup_routines_bootstrap``.

      Set the :envvar:`GPI_EXTRA` environment variable to
      ``$(cocotb-config --lib-name-path vhpi xcelium):cocotbvhpi_entry_point``
      if there are also VHDL modules in the design.

.. _custom-flows-ghdl:

GHDL
====

* Extend the ``ghdl -r`` call with the option
  ``--vpi=$(cocotb-config --lib-name-path vpi ghdl)``.

.. _custom-flows-nvc:

NVC
===

* Extend the ``nvc -r`` call with the option
  ``--load=$(cocotb-config --lib-name-path vhpi nvc)``.

.. note::
   It is recommended to add ``--preserve-case`` to build arguments.
   This is standards-compliant behavior and may become default behavior in NVC.

.. _custom-flows-cvc:

Tachyon DA CVC
==============

* Extend the ``cvc64`` call with the option
  ``+interp +acc+2 +loadvpi=$(cocotb-config --lib-name-path vpi cvc):vlog_startup_routines_bootstrap``.

.. _custom-flows-dsim:

Siemens DSim
============

* Extend the ``dsim`` call with the option
  ``-pli_lib $(cocotb-config --lib-name-path vpi dsim) +acc+rwcbfsWF``.
