# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog
COCOTB_TOPLEVEL := fatal
COCOTB_TEST_MODULES := test_fatal

PWD=$(shell pwd)

ifeq ($(TOPLEVEL_LANG),verilog)
    VERILOG_SOURCES := $(PWD)/fatal.sv
else ifeq ($(TOPLEVEL_LANG),vhdl)
    VHDL_SOURCES := $(PWD)/fatal.vhd
    ifneq ($(filter $(SIM),ius xcelium),)
        COMPILE_ARGS += -v93
    endif
endif

ifeq ($(shell echo $(SIM) | tr A-Z a-z),verilator)
    COMPILE_ARGS += --timing
endif

# squash error code from simulator and ensure the cocotb test passed
.PHONY: override_for_this_test
override_for_this_test:
	-$(MAKE) all
	$(call check_for_results_file)
	python -m cocotb_tools.combine_results &> /dev/null

include $(shell cocotb-config --makefiles)/Makefile.sim
