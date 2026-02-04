# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog

ifneq ($(TOPLEVEL_LANG),verilog)

all:
	@echo "Skipping test due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being verilog"
clean::

else ifeq ($(SIM),verilator)

all:
	@echo "verilator use LogicArrayObjects for verilog"
clean::

else

SIM ?= verilator

VERILOG_SOURCES = $(PWD)/debug_array.v

COCOTB_TOPLEVEL = debug_array
COCOTB_TEST_MODULES = test

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
