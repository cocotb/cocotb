# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog
TOPLEVEL := test
MODULE := test_first_on_coincident_triggers

PWD=$(shell pwd)

ifeq ($(TOPLEVEL_LANG),verilog)
    VERILOG_SOURCES := $(PWD)/test.sv
else ifeq ($(TOPLEVEL_LANG),vhdl)
    VHDL_SOURCES := $(PWD)/test.vhd
    ifneq ($(filter $(SIM),ius xcelium),)
        SIM_ARGS += -v93
    endif
endif

include $(shell cocotb-config --makefiles)/Makefile.sim
