# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog

ifneq ($(TOPLEVEL_LANG),verilog)

all:
	@echo "Skipping test due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being verilog"
clean::

else

COCOTB ?= $(PWD)/../../..
PWD = $(shell pwd)
VERILOG_SOURCES = $(COCOTB)/tests/test_cases/test_vpi_structure/vpi_structure.sv
TOPLEVEL := t
MODULE = vpi_structure

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
