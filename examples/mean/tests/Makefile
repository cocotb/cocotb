
TOPLEVEL_LANG ?= verilog

ifneq ($(TOPLEVEL_LANG),verilog)

all:
	@echo "Skipping example due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being verilog"
clean::

else

TOPLEVEL := mean_sv

PWD=$(shell pwd)

ifeq ($(OS),Msys)
WPWD=$(shell sh -c 'pwd -W')
else
WPWD=$(shell pwd)
endif

VHDL_SOURCES = $(WPWD)/../hdl/mean_pkg.vhd
VHDL_SOURCES += $(WPWD)/../hdl/mean.vhd

VCOM_ARGS = -mixedsvvh

GENERICS = "BUS_WIDTH=2"

VERILOG_SOURCES = $(WPWD)/../hdl/mean_sv.sv

MODULE := test_mean

include $(shell cocotb-path)/makefiles/Makefile.inc
include $(shell cocotb-path)/makefiles/Makefile.sim

endif
