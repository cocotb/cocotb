# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog
SIM ?= verilator

VERILOG_SOURCES = tops.v
COCOTB_TEST_MODULES = test_cocotb_tops
COCOTB_TOPLEVEL = verilog_top_b
COCOTB_TOPLEVEL += verilog_top_a

ifeq ($(TOPLEVEL_LANG), vhdl)

all:
	@echo "Skipping test: only applicable to Verilog"

else

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
