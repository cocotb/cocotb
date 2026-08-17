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

* Define :envvar:`COCOTB_BOOTSTRAP` using
  ``$(cocotb-config --gpi-entry-point):$(cocotb-config --libpython):$(cocotb-config --pygpi-entry-point)``
  on Linux and macOS. Use ``;`` instead of ``:`` on Windows.
* Define :envvar:`PYGPI_PYTHON_BIN` using ``$(cocotb-config --python-bin)``.
* Define :envvar:`COCOTB_TEST_MODULES` with the name of the Python module(s) containing your testcases.

See the sections below for additional settings to be done, depending on the simulator.
Use ``cocotb-config --lib-entry INTERFACE SIMULATOR`` to obtain the bootstrap library and entry point to load.
For simulators that require an explicit entry function, the result uses the
``library:entry_function`` format.

.. _custom-flows-icarus:

Icarus Verilog
==============

* Set :envvar:`GPI_IMPL` to ``$(cocotb-config --gpi-impl icarus vpi)``.
* Call the ``vvp`` executable with the option ``-m $(cocotb-config --lib-entry vpi icarus)``.

Verilator
=========

* Extend the call to ``verilator`` with these options:

   .. code-block::

      --vpi --prefix Vtop \
      -LDFLAGS "-Wl,-rpath,$(cocotb-config --lib-dir) \
          $(cocotb-config --lib-entry vpi verilator) -rdynamic" \
      $(cocotb-config --share)/lib/verilator/verilator.cpp

* Run Verilator's makefile as follows: ``CPPFLAGS="-std=c++11" make -f Vtop.mk``
* Set :envvar:`GPI_IMPL` to ``$(cocotb-config --gpi-impl verilator vpi)`` before running the model.

.. note::
   You may want to add ``--public-flat-rw`` to make all signals in the design accessible over the VPI;
   however, there is a performance penalty in doing so.

.. _custom-flows-vcs:

Synopsys VCS
============

* Create a file :file:`pli.tab` with the content ``acc+=rw,wn:*`` (or equivalent)
  to allow cocotb to access values in the design.
* Extend the ``vcs`` call with the options
  ``+vpi -P pli.tab -load $(cocotb-config --lib-entry vpi vcs)``.
* Set :envvar:`GPI_IMPL` to ``$(cocotb-config --gpi-impl vcs vpi)``.

.. _custom-flows-aldec:
.. _custom-flows-riviera:

Aldec Riviera-PRO
=================

* The ``asim`` call needs the ``+access +w_nets`` option set to allow cocotb to access values in the design.

.. tab-set::

   .. tab-item:: Design with a VHDL Toplevel

      For a design with a VHDL toplevel, call ``asim`` with the option
      ``-loadvhpi $(cocotb-config --lib-entry vhpi riviera)``.

      Set the :envvar:`GPI_IMPL` environment variable to
      ``$(cocotb-config --gpi-impl riviera vhpi)``.
      If there are also (System)Verilog modules in the design, use
      ``$(cocotb-config --gpi-impl riviera vhpi vpi)``.

   .. tab-item:: Design with a (System)Verilog Toplevel

      For a design with a (System)Verilog toplevel, call ``alog`` and ``asim`` with the option
      ``-pli $(cocotb-config --lib-entry vpi riviera)``.

      Set the :envvar:`GPI_IMPL` environment variable to
      ``$(cocotb-config --gpi-impl riviera vpi)``.
      If there are also VHDL modules in the design, use
      ``$(cocotb-config --gpi-impl riviera vpi vhpi)``.

.. _custom-flows-activehdl:

Aldec Active-HDL
================

* The ``asim`` call needs the ``+access +w_nets`` option set to allow cocotb to access values in the design.

.. tab-set::

   .. tab-item:: Design with a VHDL Toplevel

      For a design with a VHDL toplevel, call ``asim`` with the option
      ``-loadvhpi $(cocotb-config --lib-entry vhpi activehdl)``.

      Set the :envvar:`GPI_IMPL` environment variable to
      ``$(cocotb-config --gpi-impl activehdl vhpi)``.
      If there are also (System)Verilog modules in the design, use
      ``$(cocotb-config --gpi-impl activehdl vhpi vpi)``.

   .. tab-item:: Design with a (System)Verilog Toplevel

      For a design with a (System)Verilog toplevel, call ``alog`` and ``asim`` with the option
      ``-pli $(cocotb-config --lib-entry vpi activehdl)``.

      Set the :envvar:`GPI_IMPL` environment variable to
      ``$(cocotb-config --gpi-impl activehdl vpi)``.
      If there are also VHDL modules in the design, use
      ``$(cocotb-config --gpi-impl activehdl vpi vhpi)``.

.. _custom-flows-siemens:

Mentor/Siemens EDA Questa and Modelsim
======================================

Questa supports two different flows: the traditional flow using ``vsim``, which is also used by ModelSim, and a modern alternative using ``qrun``.

.. tab-set::

   .. tab-item:: Design with a VHDL Toplevel

      For a design with a VHDL toplevel, call the ``vsim`` or ``qrun`` executable with the option
      ``-foreign "cocotb_bootstrap_entry $(cocotb-config --lib-entry fli questa)"``.

      Set the :envvar:`GPI_IMPL` environment variable to
      ``$(cocotb-config --gpi-impl questa fli)``.
      If there are also (System)Verilog modules in the design, use
      ``$(cocotb-config --gpi-impl questa fli vpi)``.

   .. tab-item:: Design with a (System)Verilog Toplevel

      For a design with a (System)Verilog toplevel, call the ``vsim`` or ``qrun`` executable with the option
      ``-pli $(cocotb-config --lib-entry vpi questa)``.

      Set the :envvar:`GPI_IMPL` environment variable to
      ``$(cocotb-config --gpi-impl questa vpi)``.
      If there are also VHDL modules in the design, use
      ``$(cocotb-config --gpi-impl questa vpi fli)``.

.. _custom-flows-cadence:

Cadence Incisive and Xcelium
============================

* The ``xrun`` call (or ``xmelab`` in multi-step mode) needs the ``-access +rwc``
  (or equivalent, e.g. :samp:`-afile {afile}`) option set to allow cocotb to access values in the design.

* The ``xrun`` call (or ``xmsim`` in multi-step mode) needs the VPI library and entry point via the option
  ``-loadvpisim $(cocotb-config --lib-entry vpi xcelium)``.


* Set :envvar:`GPI_IMPL` to ``$(cocotb-config --gpi-impl xcelium vpi)``.
  If the design contains any VHDL modules, use
  ``$(cocotb-config --gpi-impl xcelium vpi vhpi)``.
  This is because directly loading the VHPI library causes an error in Xcelium,
  so always load the VPI library and supply VHPI via ``GPI_IMPL``.

.. note::
  For a design with a VHDL toplevel, call the ``xrun`` or ``xmelab`` executable with the option
  ``-NEW_VHPI_PROPAGATE_DELAY``.

.. _custom-flows-ghdl:

GHDL
====

* Extend the ``ghdl -r`` call with the option
  ``--vpi=$(cocotb-config --lib-entry vpi ghdl)``.
* Set :envvar:`GPI_IMPL` to ``$(cocotb-config --gpi-impl ghdl vpi)``.

.. _custom-flows-nvc:

NVC
===

* Extend the ``nvc -r`` call with the option
  ``--load=$(cocotb-config --lib-entry vhpi nvc)``.
* Set :envvar:`GPI_IMPL` to ``$(cocotb-config --gpi-impl nvc vhpi)``.

.. note::
   It is recommended to add ``--preserve-case`` to build arguments.
   This is standards-compliant behavior and may become default behavior in NVC.

.. _custom-flows-cvc:

Tachyon DA CVC
==============

* Extend the ``cvc64`` call with the option
  ``+interp +acc+2 +loadvpi=$(cocotb-config --lib-entry vpi cvc)``.
* Set :envvar:`GPI_IMPL` to ``$(cocotb-config --gpi-impl cvc vpi)``.

.. _custom-flows-dsim:

Siemens DSim
============

* Extend the ``dsim`` call with the option
  ``-pli_lib $(cocotb-config --lib-entry vpi dsim) +acc+rwcbfsWF``.
* Set :envvar:`GPI_IMPL` to ``$(cocotb-config --gpi-impl dsim vpi)``.
