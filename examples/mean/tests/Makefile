
TOPLEVEL_LANG ?= verilog

ifeq ($(TOPLEVEL_LANG),verilog)
  VERILOG_SOURCES = $(PWD)/../hdl/mean_sv.sv
  TOPLEVEL := mean_sv
else ifeq ($(TOPLEVEL_LANG),vhdl)
  TOPLEVEL := mean
else
  $(error "A valid value (verilog or vhdl) was not provided for TOPLEVEL_LANG=$(TOPLEVEL_LANG)")
endif

PWD=$(shell pwd)

VHDL_SOURCES = $(PWD)/../hdl/mean_pkg.vhd
VHDL_SOURCES += $(PWD)/../hdl/mean.vhd

ifeq ($(SIM),questa)
COMPILE_ARGS = -mixedsvvh
endif

MODULE := test_mean

ifneq ($(filter $(SIM),ius xcelium),)
    SIM_ARGS += -v93
endif

include $(shell cocotb-config --makefiles)/Makefile.sim
