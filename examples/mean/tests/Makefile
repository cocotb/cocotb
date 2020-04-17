
TOPLEVEL_LANG ?= verilog

ifneq ($(TOPLEVEL_LANG),verilog)

all:
	@echo "Skipping example due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being verilog"
clean::

else

TOPLEVEL := mean_sv

PWD=$(shell pwd)

VHDL_SOURCES = $(PWD)/../hdl/mean_pkg.vhd
VHDL_SOURCES += $(PWD)/../hdl/mean.vhd

ifeq ($(SIM),questa)
COMPILE_ARGS = -mixedsvvh
endif

VERILOG_SOURCES = $(PWD)/../hdl/mean_sv.sv

MODULE := test_mean

ifneq ($(filter $(SIM),ius xcelium),)
    SIM_ARGS += -v93
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
