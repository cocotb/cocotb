# Override this variable to use a VHDL toplevel instead of SystemVerilog
TOPLEVEL_LANG ?= sv

# At the moment the only simulator supporting mixed language VHPI/VPI is Aldec
SIM?=aldec

TOPLEVEL = endian_swapper_mixed

PWD=$(shell pwd)
COCOTB=$(PWD)/../../..

ifeq ($(OS),Msys)
WPWD=$(shell sh -c 'pwd -W')
else
WPWD=$(shell pwd)
endif

VERILOG_SOURCES = $(WPWD)/../../endian_swapper/hdl/endian_swapper.sv
VHDL_SOURCES    = $(WPWD)/../../endian_swapper/hdl/endian_swapper.vhdl

ifeq ($(TOPLEVEL_LANG),sv)
    VERILOG_SOURCES += $(WPWD)/../hdl/toplevel.sv
    GPI_IMPL=vpi
ifeq ($(SIM),aldec)
    GPI_EXTRA=vhpi
endif
ifeq ($(SIM),modelsim)
    GPI_EXTRA=fli
endif
endif

ifeq ($(TOPLEVEL_LANG),vhdl)
    $(error "VHDL toplevel not yet implemented")
    VHDL_SOURCES += $(WPWD)/../hdl/toplevel.vhdl
ifeq ($(SIM),aldec)
    GPI_IMPL=vhpi
endif
ifeq ($(SIM),modelsim)
    GPI_IMPL=fli
endif
    GPI_EXTRA=vpi
endif


MODULE=test_mixed_language

include $(COCOTB)/makefiles/Makefile.inc
include $(COCOTB)/makefiles/Makefile.sim

