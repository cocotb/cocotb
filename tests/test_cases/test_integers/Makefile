# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

SIM ?= icarus
TOPLEVEL_LANG ?= verilog

TOPLEVEL=top
COCOTB_TEST_MODULES=test_integers

ifeq ($(TOPLEVEL_LANG),verilog)
VERILOG_SOURCES = $(shell pwd)/integers.sv
else ifeq ($(TOPLEVEL_LANG),vhdl)
VHDL_SOURCES = $(shell pwd)/integers.vhdl
endif

include $(shell cocotb-config --makefiles)/Makefile.sim
