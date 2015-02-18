
TOPLEVEL_LANG ?= verilog

PWD=$(shell pwd)
COCOTB=$(PWD)/../../..

ifeq ($(OS),Msys)
WPWD=$(shell sh -c 'pwd -W')
else
WPWD=$(shell pwd)
endif

ifeq ($(TOPLEVEL_LANG),verilog)
    VHDL_SOURCES = $(WPWD)/../hdl/mean_pkg.vhd
    VHDL_SOURCES += $(WPWD)/../hdl/mean.vhd

    VCOM_ARGS = -mixedsvvh
    export VCOM_ARGS

    VERILOG_SOURCES = $(WPWD)/../hdl/mean_sv.sv
    TOPLEVEL = mean_sv
    GPI_IMPL = vpi
endif

ifeq ($(TOPLEVEL_LANG),vhdl)
    VHDL_SOURCES = $(WPWD)/../hdl/mean_pkg.vhd
    VHDL_SOURCES += $(WPWD)/../hdl/mean.vhd
    TOPLEVEL = mean
    GPI_IMPL=vhpi
endif

export TOPLEVEL_LANG

GENERICS = "BUS_WIDTH=2"
export GENERICS

MODULE ?= test_mean

include $(COCOTB)/makefiles/Makefile.inc
include $(COCOTB)/makefiles/Makefile.sim
