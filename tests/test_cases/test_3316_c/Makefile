# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
TOPLEVEL_LANG ?= verilog
SIM ?= verilator
COCOTB_TEST_MODULES := test_3316_c
VERILOG_SOURCES := ../test_3316/test_3316.sv
COCOTB_TOPLEVEL := test_3316

EXTRA_ARGS="--timing"

ifneq ($(shell echo $(TOPLEVEL_LANG) | tr A-Z a-z),verilog)
all:
	@echo "Skipping test since only Verilog is supported"
else ifeq ($(filter verilator,$(shell echo $(SIM) | tr A-Z a-z)),)
all:
	@echo "Skipping test since only Verilator is supported"
else ifneq ($(shell ./check_version 2>/dev/null 1>&2; echo $$?),0)
all:
	@echo "Skipping test since it requires newer version of cocotb"
else
include $(shell cocotb-config --makefiles)/Makefile.sim
endif
