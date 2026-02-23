# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

PROJ_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

TOPLEVEL_LANG ?= verilog

ifeq ($(TOPLEVEL_LANG),verilog)
VERILOG_SOURCES := $(PROJ_DIR)/test.sv
else ifeq ($(TOPLEVEL_LANG),vhdl)
VHDL_SOURCES := $(PROJ_DIR)/test.vhd
endif

COCOTB_TOPLEVEL := test

ifneq ($(filter $(SIM),ius xcelium),)
COMPILE_ARGS += -v93
endif

export COCOTB_TEST_MODULES := test_similar_scope_name
export COCOTB_LOG_LEVEL := DEBUG

include $(shell cocotb-config --makefiles)/Makefile.sim
