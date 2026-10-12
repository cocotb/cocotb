# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

# Regression test for indexing a multi-dimensional array that is a field of a
# VHDL record. This exercises the VHPI backend (NVC), so it is VHDL-only.

SIM ?= nvc
TOPLEVEL_LANG ?= vhdl

ifeq ($(TOPLEVEL_LANG),vhdl)
	VHDL_SOURCES := $(PWD)/test_vhdl_record_array_indexing.vhdl
else
    $(error "Unsupported TOPLEVEL_LANG=$(TOPLEVEL_LANG)")
endif

COCOTB_TOPLEVEL := test_vhdl_record_array_indexing
COCOTB_TEST_MODULES := test_vhdl_record_array_indexing

include $(shell cocotb-config --makefiles)/Makefile.sim
