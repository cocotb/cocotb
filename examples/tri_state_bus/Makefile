# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

TOPLEVEL_LANG ?= verilog

ifeq ($(TOPLEVEL_LANG),verilog)
  VERILOG_SOURCES = $(shell pwd)/bus_master.sv
else ifeq ($(TOPLEVEL_LANG),vhdl)
  VHDL_SOURCES = $(shell pwd)/bus_master.vhdl
endif

COCOTB_TEST_MODULES = test_tri_state_bus
COCOTB_TOPLEVEL = bus_master

include $(shell cocotb-config --makefiles)/Makefile.sim
