# Override this variable to use a VHDL toplevel instead of SystemVerilog
TOPLEVEL_LANG ?= verilog

# At the moment the only simulator supporting mixed language VHPI/VPI is Aldec
SIM?=aldec

TOPLEVEL = endian_swapper_mixed

PWD=$(shell pwd)

ifeq ($(OS),Msys)
WPWD=$(shell sh -c 'pwd -W')
else
WPWD=$(shell pwd)
endif

VERILOG_SOURCES = $(WPWD)/../../endian_swapper/hdl/endian_swapper.sv
VHDL_SOURCES    = $(WPWD)/../../endian_swapper/hdl/endian_swapper.vhdl

ifeq ($(TOPLEVEL_LANG),verilog)
    VERILOG_SOURCES += $(WPWD)/../hdl/toplevel.sv
else ifeq ($(TOPLEVEL_LANG),vhdl)
    $(error "VHDL toplevel not yet implemented")
    VHDL_SOURCES += $(WPWD)/../hdl/toplevel.vhdl
else
    $(error "A valid value (verilog or vhdl) was not provided for TOPLEVEL_LANG=$(TOPLEVEL_LANG)")
endif


MODULE=test_mixed_language

include $(shell cocotb-config --makefiles)/Makefile.inc
include $(shell cocotb-config --makefiles)/Makefile.sim
