# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog
COCOTB_TOPLEVEL := test
COCOTB_TEST_MODULES := test_first_on_coincident_triggers

PWD=$(shell pwd)

ifeq ($(TOPLEVEL_LANG),verilog)
    VERILOG_SOURCES := $(PWD)/test.sv
else ifeq ($(TOPLEVEL_LANG),vhdl)
    VHDL_SOURCES := $(PWD)/test.vhd
    ifneq ($(filter $(SIM),ius xcelium),)
        COMPILE_ARGS += -v93
    endif
endif

ifeq ($(shell echo $(SIM) | tr A-Z a-z),verilator)
    COMPILE_ARGS += --timing
endif

include $(shell cocotb-config --makefiles)/Makefile.sim
