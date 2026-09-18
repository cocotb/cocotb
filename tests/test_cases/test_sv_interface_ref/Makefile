# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog
VERILOG_SOURCES = $(shell pwd)/top.sv
COCOTB_TEST_MODULES = test_sv_if_ref
COCOTB_TOPLEVEL = top

# Simulator behavior:
# Verilator exposes interface ports as vpiRefObj, which must be resolved via
#   vpiActual to reach the interface instance. Arrays of interface references
#   are only visible as individual elements, so the array itself is a
#   pseudo-region.
# Xcelium exposes interface ports as vpiRefObj too, but supports
#   vpiInterfaceArray, so an array of references is a real array object.

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
