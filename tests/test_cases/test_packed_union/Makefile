# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog

ifneq ($(TOPLEVEL_LANG),verilog)

all:
	@echo "Skipping test due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being verilog"
clean::

else

VERILOG_SOURCES = $(PWD)/test_packed_union.sv
COCOTB_TOPLEVEL = test_packed_union
COCOTB_TEST_MODULES = test_packed_union

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
