# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog
SIM ?= icarus

ifeq ($(TOPLEVEL_LANG),verilog)

VERILOG_SOURCES = tops.v
TOPLEVEL = verilog_top_a

else ifeq ($(TOPLEVEL_LANG),vhdl)

VHDL_SOURCES = tops.vhdl
TOPLEVEL = vhdl_top_a

endif

COCOTB_TEST_MODULES = test_cocotb_tops

include $(shell cocotb-config --makefiles)/Makefile.sim
