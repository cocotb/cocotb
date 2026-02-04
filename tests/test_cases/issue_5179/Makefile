# Makefile

# simulator
#SIM ?= verilator
SIM ?= GHDL

# hdl
TOPLEVEL_LANG ?= vhdl

# VHDL Source
VHDL_SOURCES += debug_array_vhdl.vhdl

# COCOTB_TOPLEVEL is the name of the toplevel module in your Verilog or VHDL file
COCOTB_TOPLEVEL = debug_array_vhdl

# COCOTB_TEST_MODULES is the basename of the Python test file(s)
COCOTB_TEST_MODULES = test

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim
