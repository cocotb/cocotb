# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= vhdl

ifneq ($(TOPLEVEL_LANG),vhdl)

all:
	@echo "Skipping test due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being vhdl"
clean::

else

SIM ?= ghdl

VHDL_SOURCES = $(PWD)/debug_array.vhdl

COCOTB_TOPLEVEL = debug_array
COCOTB_TEST_MODULES = test

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
