# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog
VERILOG_SOURCES = $(shell pwd)/top.sv
MODULE = test_sv_if
TOPLEVEL = top

# simulator behavior:
# icarus sees SV interfaces as vpiModule but doesn't discover signals inside them
# verilator sees SV interfaces as vpiModule and discovers signals inside them
# commercial simulators all see SV interfaces as vpiInterface and discover signals inside them


ifneq ($(TOPLEVEL_LANG),verilog)
all:
	@echo "Skipping test due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being verilog"
clean::
else
ifeq ($(filter questa xcelium vcs riviera verilator,$(shell echo $(SIM) | tr A-Z a-z)),)
all::
	@echo "skipping simulator $(SIM) because it might not support SV interfaces"	
clean::
else
include $(shell cocotb-config --makefiles)/Makefile.sim
endif
endif
