# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

TOPLEVEL_LANG ?= verilog

ifeq ($(TOPLEVEL_LANG),verilog)
  VERILOG_SOURCES += $(shell pwd)/clkgen.sv
  VERILOG_SOURCES += $(shell pwd)/dut.sv
  VERILOG_SOURCES += $(shell pwd)/tb.sv
else ifeq ($(TOPLEVEL_LANG),vhdl)
  VHDL_SOURCES += $(shell pwd)/clkgen.vhdl
  VHDL_SOURCES += $(shell pwd)/dut.vhdl
  VHDL_SOURCES += $(shell pwd)/tb.vhdl
endif

MODULE = test_clkgen
TOPLEVEL = tb

ifneq ($(filter $(SIM),ius xcelium),)
  SIM_ARGS += -v93
endif

include $(shell cocotb-config --makefiles)/Makefile.sim
