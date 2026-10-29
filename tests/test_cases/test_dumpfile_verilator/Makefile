# Copyright cocotb contributors
# Copyright (c) 2015 Potential Ventures Ltd
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog
SIM ?= verilator
EXTRA_ARGS += --trace

ifneq ($(SIM),verilator)

all:
	@echo "Skipping test due to SIM=$(SIM) not being Verilator"
clean::

else

VERILOG_SOURCES = $(PWD)/test_dumpfile_verilator.sv
COCOTB_TOPLEVEL = test_dumpfile_verilator
COCOTB_TEST_MODULES = test_dumpfile_verilator

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
