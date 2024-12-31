# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog

ifneq ($(TOPLEVEL_LANG),verilog)

sim:
	@echo Only Verilog is supported for this test, skipping...

else

COCOTB_TEST_MODULES := test_3270
VERILOG_SOURCES := $(PWD)/test_3270.sv
COCOTB_TOPLEVEL := trigger_counter

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
