
TOPLEVEL := mean_sv
TOPLEVEL_LANG ?= verilog

PWD=$(shell pwd)
COCOTB=$(PWD)/../../..

ifeq ($(OS),Msys)
WPWD=$(shell sh -c 'pwd -W')
else
WPWD=$(shell pwd)
endif

VHDL_SOURCES = $(WPWD)/../hdl/mean_pkg.vhd
VHDL_SOURCES += $(WPWD)/../hdl/mean.vhd

VCOM_ARGS = -mixedsvvh
export VCOM_ARGS

GENERICS = "BUS_WIDTH=2"
export GENERICS

VERILOG_SOURCES = $(WPWD)/../hdl/mean_sv.sv
GPI_IMPL := vpi

export TOPLEVEL_LANG

MODULE ?= test_mean

include $(COCOTB)/makefiles/Makefile.inc
include $(COCOTB)/makefiles/Makefile.sim
