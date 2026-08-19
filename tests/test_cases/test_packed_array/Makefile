# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog

ifeq ($(SIM),)
all:
	@echo "Skipping test_packed_array since icarus flattens multi-dimensional arrays (gh-2595)"

clean::
# nothing to clean, just define target in this branch

else ifneq ($(filter $(shell echo $(SIM) | tr A-Z a-z),icarus),)
all:
	@echo "Skipping test_packed_array since $(SIM) flattens multi-dimensional arrays (gh-2595)"

clean::
# nothing to clean, just define target in this branch

else ifneq ($(filter $(shell echo $(SIM) | tr A-Z a-z),riviera),)
all:
	@echo "Skipping test_packed_array since $(SIM) crashes on packed structs (gh-4753)"

clean::
# nothing to clean, just define target in this branch

else ifneq ($(TOPLEVEL_LANG),verilog)
all:
	@echo "Skipping test_packed_array since the design is SystemVerilog and TOPLEVEL_LANG is $(TOPLEVEL_LANG)"

clean::
# nothing to clean, just define target in this branch

else

PWD=$(shell pwd)

VERILOG_SOURCES = $(PWD)/packed_array.sv

COCOTB_TEST_MODULES = test_packed_array
COCOTB_TOPLEVEL := packed_array

ifeq ($(SIM), verilator)
	EXTRA_ARGS = "--timing"
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
