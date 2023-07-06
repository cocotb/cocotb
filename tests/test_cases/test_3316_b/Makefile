# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
TOPLEVEL_LANG ?= verilog
SIM ?= verilator
MODULE := test_3316_b
VERILOG_SOURCES := ../test_3316/test_3316.sv
TOPLEVEL := test_3316

EXTRA_ARGS="+define+TEST_CLK_EXTERNAL=1"

ifneq ($(shell echo $(TOPLEVEL_LANG) | tr A-Z a-z),verilog)
all:
	@echo "Skipping test since only Verilog is supported"
else ifeq ($(filter verilator,$(shell echo $(SIM) | tr A-Z a-z)),)
all:
	@echo "Skipping test since only Verilator is supported"
else
include $(shell cocotb-config --makefiles)/Makefile.sim
endif
