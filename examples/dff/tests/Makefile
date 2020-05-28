# Copyright (c) 2016 Technische Universitaet Dresden, Germany
# Chair for VLSI-Design, Diagnostic and Architecture
# Author: Martin Zabel
# All rights reserved.

CWD=$(shell pwd)

TOPLEVEL_LANG ?=verilog

ifeq ($(TOPLEVEL_LANG),verilog)
  VERILOG_SOURCES =$(CWD)/../hdl/dff.v
else ifeq ($(TOPLEVEL_LANG),vhdl)
  VHDL_SOURCES =$(CWD)/../hdl/dff.vhdl
else
  $(error "A valid value (verilog or vhdl) was not provided for TOPLEVEL_LANG=$(TOPLEVEL_LANG)")
endif

TOPLEVEL = dff
MODULE := $(TOPLEVEL)_cocotb
COCOTB_HDL_TIMEUNIT=1us
COCOTB_HDL_TIMEPRECISION=1us

CUSTOM_SIM_DEPS=$(CWD)/Makefile

ifeq ($(SIM),questa)
    SIM_ARGS=-t 1ps
endif

ifneq ($(filter $(SIM),ius xcelium),)
    SIM_ARGS += -v93
endif

include $(shell cocotb-config --makefiles)/Makefile.sim
