TOPLEVEL = testbench

VHDL_SOURCES = $(COCOTB)/tests/designs/vhdl_configurations/dut.vhd
ifeq ($(TOPLEVEL_LANG),vhdl)
   	VHDL_SOURCES += $(COCOTB)/tests/designs/vhdl_configurations/testbench.vhd
    GPI_IMPL := vhpi
endif
VHDL_SOURCES += $(COCOTB)/tests/designs/vhdl_configurations/configurations.vhd

ifeq ($(TOPLEVEL_LANG),verilog)
    VERILOG_SOURCES = $(COCOTB)/tests/designs/vhdl_configurations/testbench.sv
    GPI_IMPL := vpi
endif

ifneq ($(SIM),)
	include $(COCOTB)/makefiles/Makefile.inc
	include $(COCOTB)/makefiles/Makefile.sim
else
all:
	@echo "Skipping test as VHDL not supported on Icarus"
clean::
endif

