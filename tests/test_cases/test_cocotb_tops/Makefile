# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog
SIM ?= icarus

VERILOG_SOURCES = tops.v
COCOTB_TOPLEVEL = verilog_top_a
COCOTB_TEST_MODULES = test_cocotb_tops

include $(shell cocotb-config --makefiles)/Makefile.sim
