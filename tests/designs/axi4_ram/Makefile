# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog

ifneq ($(TOPLEVEL_LANG),verilog)

all:
	@echo "Skipping test due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being verilog"
clean::

else

TOPLEVEL := top

PWD=$(shell pwd)

COCOTB?=$(PWD)/../../..

VERILOG_SOURCES = $(COCOTB)/tests/designs/axi4_ram/axi_register_rd.v
VERILOG_SOURCES += $(COCOTB)/tests/designs/axi4_ram/axi_register_wr.v
VERILOG_SOURCES += $(COCOTB)/tests/designs/axi4_ram/axi_register.v
VERILOG_SOURCES += $(COCOTB)/tests/designs/axi4_ram/priority_encoder.v
VERILOG_SOURCES += $(COCOTB)/tests/designs/axi4_ram/arbiter.v
VERILOG_SOURCES += $(COCOTB)/tests/designs/axi4_ram/axi_interconnect.v
VERILOG_SOURCES += $(COCOTB)/tests/designs/axi4_ram/axi_ram.v
VERILOG_SOURCES += $(COCOTB)/tests/designs/axi4_ram/top.v

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
