# Copyright cocotb contributors
# Copyright (c) 2015 Potential Ventures Ltd
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog

ifneq ($(TOPLEVEL_LANG),verilog)

all:
	@echo "Skipping test due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being verilog"
clean::

else

VERILOG_SOURCES = $(PWD)/endian_swapper.sv
COCOTB_TOPLEVEL = endian_swapper_sv
COCOTB_TEST_MODULES = test_iteration_es

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
