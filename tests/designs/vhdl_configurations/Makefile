TOPLEVEL_LANG ?= vhdl

ifneq ($(TOPLEVEL_LANG),vhdl)

# Currently, there is an issue with file dependency when dealing with a Mixed Language Simulation like this.
# With the current process, all the VHDL is compiled first and then all the Verilog which doesn't work with a
# dependency like below.  Compile order would need to be:
#    1. dut.vhd
#    2. testbench.vhd or testbench.v
#    3. configurations.vhd
all:
	@echo "Skipping test due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being vhdl"
clean::

else

TOPLEVEL = testbench

PWD=$(shell pwd)

COCOTB?=$(PWD)/../../..

VHDL_SOURCES = $(COCOTB)/tests/designs/vhdl_configurations/dut.vhd
ifeq ($(TOPLEVEL_LANG),verilog)
    VERILOG_SOURCES = $(COCOTB)/tests/designs/vhdl_configurations/testbench.sv
else ifeq ($(TOPLEVEL_LANG),vhdl)
    VHDL_SOURCES += $(COCOTB)/tests/designs/vhdl_configurations/testbench.vhd
else
    $(error A valid value (verilog or vhdl) was not provided for TOPLEVEL_LANG=$(TOPLEVEL_LANG))
endif
VHDL_SOURCES += $(COCOTB)/tests/designs/vhdl_configurations/configurations.vhd

ifneq ($(filter $(SIM),ius xcelium),)
    SIM_ARGS += -v93
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
