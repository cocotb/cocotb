# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

# simulator
#SIM ?= verilator
SIM ?= GHDL

# hdl
#TOPLEVEL_LANG ?= verilog
TOPLEVEL_LANG ?= vhdl

#VERILOG_SOURCES += debug_array_verilog.v
VHDL_SOURCES += debug_array.vhdl

# COCOTB_TOPLEVEL is the name of the toplevel module in your Verilog or VHDL file
COCOTB_TOPLEVEL = debug_array

# COCOTB_TEST_MODULES is the basename of the Python test file(s)
COCOTB_TEST_MODULES = test

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim
