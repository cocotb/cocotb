# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

TOPLEVEL_LANG ?= verilog

VERILOG_SOURCES = $(shell pwd)/simple_memory.sv

COCOTB_TEST_MODULES = test_simple_memory
COCOTB_TOPLEVEL = simple_memory

include $(shell cocotb-config --makefiles)/Makefile.sim
