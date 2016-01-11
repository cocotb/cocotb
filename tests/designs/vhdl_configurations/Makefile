TOPLEVEL_LANG ?= verilog

TOPLEVEL = testbench

VHDL_SOURCES = $(COCOTB)/tests/designs/vhdl_configurations/dut.vhd
ifeq ($(TOPLEVEL_LANG),verilog)
    VERILOG_SOURCES = $(COCOTB)/tests/designs/vhdl_configurations/testbench.sv
else ifeq ($(TOPLEVEL_LANG),vhdl)
   	VHDL_SOURCES += $(COCOTB)/tests/designs/vhdl_configurations/testbench.vhd
else
    $(error "A valid value (verilog or vhdl) was not provided for TOPLEVEL_LANG=$(TOPLEVEL_LANG)")
endif
VHDL_SOURCES += $(COCOTB)/tests/designs/vhdl_configurations/configurations.vhd

include $(COCOTB)/makefiles/Makefile.inc
include $(COCOTB)/makefiles/Makefile.sim

