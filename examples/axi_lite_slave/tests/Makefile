
TOPLEVEL_LANG ?= verilog
PWD=$(shell pwd)
TOPDIR=$(PWD)/..
COCOTB=$(PWD)/../../..
PYTHONPATH := ./model:$(PYTHONPATH)

export PYTHONPATH

EXTRA_ARGS+=-I$(TOPDIR)/hdl/

#DUT
VERILOG_SOURCES = $(TOPDIR)/hdl/axi_lite_slave.v
VERILOG_SOURCES += $(TOPDIR)/hdl/axi_lite_demo.v

#Test Bench
VERILOG_SOURCES += $(TOPDIR)/hdl/tb_axi_lite_slave.v

TOPLEVEL = tb_axi_lite_slave

GPI_IMPL := vpi

export TOPLEVEL_LANG
MODULE=test_axi_lite_slave

include $(COCOTB)/makefiles/Makefile.inc
include $(COCOTB)/makefiles/Makefile.sim

