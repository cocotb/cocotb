# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog

COCOTB_TOPLEVEL := tb_top

PWD=$(shell pwd)

COCOTB?=$(PWD)/../../..

ifeq ($(TOPLEVEL_LANG),verilog)
    VERILOG_SOURCES = $(COCOTB)/tests/designs/plusargs_module/tb_top.v
else ifeq ($(TOPLEVEL_LANG),vhdl)
    VHDL_SOURCES =  $(COCOTB)/tests/designs/plusargs_module/tb_top.vhd
else
    $(error A valid value (verilog or vhdl) was not provided for TOPLEVEL_LANG=$(TOPLEVEL_LANG))
endif

ifneq ($(filter $(SIM),ius xcelium),)
    COMPILE_ARGS += -v93
endif

ifeq ($(shell echo $(SIM) | tr A-Z a-z),verilator)
    COMPILE_ARGS += --timing
endif

include $(shell cocotb-config --makefiles)/Makefile.sim
