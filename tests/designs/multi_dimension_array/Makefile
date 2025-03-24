# Copyright cocotb contributors
# Copyright (c) 2016 Potential Ventures Ltd
# Copyright (c) 2016 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog

COCOTB_TOPLEVEL := cocotb_array

ifneq ($(TOPLEVEL_LANG),verilog)

all:
	@echo "Skipping test due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being verilog"
clean::

else

PWD=$(shell pwd)

COCOTB?=$(PWD)/../../..

VERILOG_SOURCES = $(COCOTB)/tests/designs/multi_dimension_array/cocotb_array_pkg.sv \
                  $(COCOTB)/tests/designs/multi_dimension_array/cocotb_array.sv

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
