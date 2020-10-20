# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

TOPLEVEL_LANG ?= verilog

ifeq ($(TOPLEVEL_LANG),verilog)
  VERILOG_SOURCES = $(shell pwd)/dffs.sv
else ifeq ($(TOPLEVEL_LANG),vhdl)
  VHDL_SOURCES = $(shell pwd)/dffs.vhdl
endif

MODULE = test_latency
TOPLEVEL = dffs
PLUSARGS+=-fst

include $(shell cocotb-config --makefiles)/Makefile.sim
