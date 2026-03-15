# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

export DUT=verilog_top_a

TOPLEVEL_LANG ?= verilog
SIM ?= icarus

VERILOG_SOURCES = tops.v
COCOTB_TEST_MODULES = test_cocotb_tops

ifeq ($(TOPLEVEL_LANG), vhdl)

all:
	@echo "Skipping test: only applicable to Verilog"

else

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
