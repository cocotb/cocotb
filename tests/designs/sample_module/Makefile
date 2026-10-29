# Copyright cocotb contributors
# Copyright (c) 2013, 2018 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog

COCOTB_TOPLEVEL := sample_module

PWD=$(shell pwd)

COCOTB?=$(PWD)/../../..

ifeq ($(TOPLEVEL_LANG),verilog)
    VERILOG_SOURCES = $(COCOTB)/tests/designs/sample_module/sample_module.sv
else ifeq ($(TOPLEVEL_LANG),vhdl)
    VHDL_SOURCES =  $(COCOTB)/tests/designs/sample_module/sample_module_package.vhdl $(COCOTB)/tests/designs/sample_module/sample_module_1.vhdl $(COCOTB)/tests/designs/sample_module/sample_module.vhdl

    ifneq ($(filter $(SIM),ius xcelium),)
        COMPILE_ARGS += -v93
    endif
else
    $(error A valid value (verilog or vhdl) was not provided for TOPLEVEL_LANG=$(TOPLEVEL_LANG))
endif

include $(shell cocotb-config --makefiles)/Makefile.sim
