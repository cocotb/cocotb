# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

ifeq ($(TOPLEVEL_LANG),vhdl)
	VHDL_SOURCES := $(PWD)/test_logic_array_indexing.vhdl
else ifeq ($(TOPLEVEL_LANG),verilog)
	VERILOG_SOURCES := $(PWD)/test_logic_array_indexing.v
else
    $(error "Unsupported TOPLEVEL_LANG=$(TOPLEVEL_LANG)")
endif

COCOTB_TOPLEVEL := test_logic_array_indexing
COCOTB_TEST_MODULES := test_logic_array_indexing

include $(shell cocotb-config --makefiles)/Makefile.sim
