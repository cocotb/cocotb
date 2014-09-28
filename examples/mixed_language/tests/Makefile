# Override this variable to use a VHDL toplevel instead of SystemVerilog
TOPLEVEL_LANG ?= sv

# At the moment the only simulator supporting mixed language VHPI/VPI is Aldec
SIM?=aldec

TOPLEVEL = endian_swapper_mixed

PWD=$(shell pwd)
COCOTB=$(PWD)/../../..

VERILOG_SOURCES = $(PWD)/../../endian_swapper/hdl/endian_swapper.sv
VHDL_SOURCES    = $(PWD)/../../endian_swapper/hdl/endian_swapper.vhdl

ifeq ($(TOPLEVEL_LANG),sv)
    VERILOG_SOURCES += $(PWD)/../hdl/toplevel.sv
endif

ifeq ($(TOPLEVEL_LANG),vhdl)
    $(error "VHDL toplevel not yet implemented")
    VHDL_SOURCES += $(PWD)/../hdl/toplevel.vhdl
endif


MODULE=test_mixed_language

include $(COCOTB)/makefiles/Makefile.inc
include $(COCOTB)/makefiles/Makefile.sim

