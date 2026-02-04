# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause


# simulator
SIM ?= verilator

# hdl
TOPLEVEL_LANG ?= verilog

VERILOG_SOURCES += debug_array.v

# COCOTB_TOPLEVEL is the name of the toplevel module in your Verilog or VHDL file
COCOTB_TOPLEVEL = debug_array

# COCOTB_TEST_MODULES is the basename of the Python test file(s)
COCOTB_TEST_MODULES = test

# include cocotb's make rules to take care of the simulator setup
ifeq ($(TOPLEVEL_LANG),verilog)
include $(shell cocotb-config --makefiles)/Makefile.sim
endif
