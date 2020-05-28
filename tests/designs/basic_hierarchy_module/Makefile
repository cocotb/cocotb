# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog

ifneq ($(TOPLEVEL_LANG),verilog)

all:
	@echo "Skipping test due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being verilog"
clean::

else

TOPLEVEL := basic_hierarchy_module

PWD=$(shell pwd)

COCOTB?=$(PWD)/../../..

VERILOG_SOURCES = $(COCOTB)/tests/designs/basic_hierarchy_module/basic_hierarchy_module.v

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
