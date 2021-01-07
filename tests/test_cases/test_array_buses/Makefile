TOPLEVEL_LANG ?= verilog
PWD=$(shell pwd)
TOPLEVEL := array_buses

ifeq ($(TOPLEVEL_LANG),verilog)
    VERILOG_SOURCES = $(PWD)/array_buses.sv
else
ifeq ($(TOPLEVEL_LANG), vhdl)
    VHDL_SOURCES = $(PWD)/array_buses.vhd
else
    $(error "A valid value (verilog or vhdl) was not provided for TOPLEVEL_LANG=$(TOPLEVEL_LANG)")
endif
endif
include $(shell cocotb-config --makefiles)/Makefile.sim


MODULE = test_array_buses
