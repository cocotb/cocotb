# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog
VERILOG_SOURCES = $(shell pwd)/top.sv
COCOTB_TEST_MODULES = test_sv_if_ref
COCOTB_TOPLEVEL = top

# Verilator exposes array-port elements individually; Xcelium uses vpiRefObj
# targeting vpiInterfaceArray. Both become pseudo-regions in cocotb.

ifneq ($(TOPLEVEL_LANG),verilog)
all:
	@echo "Skipping test due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being verilog"
clean::
else
ifeq ($(filter xcelium ius verilator,$(shell echo $(SIM) | tr A-Z a-z)),)
all::
	@echo "Skipping simulator $(SIM) because it might not support SV interface references"
clean::
else
include $(shell cocotb-config --makefiles)/Makefile.sim
endif
endif
