# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog

TOPLEVEL := cocotb_defaultless_parameter

ifneq ($(TOPLEVEL_LANG),verilog)

all:
	@echo "Skipping test due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being verilog"
clean::

else

PWD=$(shell pwd)

COCOTB?=$(PWD)/../../..

VERILOG_SOURCES = $(COCOTB)/tests/designs/defaultless_parameter_module/cocotb_defaultless_parameter.sv
# Needed for defaultless parameter support in Xcelium
EXTRA_ARGS += -newsv

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
