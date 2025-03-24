# Copyright cocotb contributors
# Copyright (c) 2016 Potential Ventures Ltd
# Copyright (c) 2016 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog

COCOTB_TOPLEVEL := array_module

PWD=$(shell pwd)

COCOTB?=$(PWD)/../../..

ifeq ($(TOPLEVEL_LANG),verilog)
    VERILOG_SOURCES = $(COCOTB)/tests/designs/array_module/array_module.sv
else ifeq ($(TOPLEVEL_LANG),vhdl)
    ifneq ($(filter $(SIM),ius xcelium),)
        COMPILE_ARGS += -v93
    endif
ifeq ($(shell echo $(SIM) | tr A-Z a-z),aldec)
    VHDL_SOURCES =  $(COCOTB)/tests/designs/array_module/array_module_pack.vhd $(COCOTB)/tests/designs/array_module/array_module_aldec.vhd
else
    VHDL_SOURCES =  $(COCOTB)/tests/designs/array_module/array_module_pack.vhd $(COCOTB)/tests/designs/array_module/array_module.vhd
endif
else
    $(error A valid value (verilog or vhdl) was not provided for TOPLEVEL_LANG=$(TOPLEVEL_LANG))
endif

include $(shell cocotb-config --makefiles)/Makefile.sim
