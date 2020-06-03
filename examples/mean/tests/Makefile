# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

TOPLEVEL_LANG ?= verilog

PWD=$(shell pwd)

ifeq ($(TOPLEVEL_LANG),verilog)
    VERILOG_SOURCES = $(PWD)/../hdl/mean.sv
else ifeq ($(TOPLEVEL_LANG),vhdl)
    VHDL_SOURCES = $(PWD)/../hdl/mean_pkg.vhd
    VHDL_SOURCES += $(PWD)/../hdl/mean.vhd
else
    $(error "A valid value (verilog or vhdl) was not provided for TOPLEVEL_LANG=$(TOPLEVEL_LANG)")
endif

TOPLEVEL := mean
MODULE := test_mean

ifneq ($(filter $(SIM),ius xcelium),)
    SIM_ARGS += -v93
endif

ifeq ($(SIM),verilator)
    EXTRA_ARGS += $(PWD)/verilator_waiver.vlt
endif

include $(shell cocotb-config --makefiles)/Makefile.sim
