# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

VERILOG_SOURCES = $(shell pwd)/top.sv
MODULE = test_sv_if
TOPLEVEL = top

# simulator behavior:
# icarus sees SV interfaces as vpiModule but doesn't discover signals inside them
# verilator sees SV interfaces as vpiModule and discovers signals inside them
# commercial simulators all see SV interfaces as vpiInterface and discover signals inside them


ifeq ($(filter questa xcelium vcs riviera verilator icarus,$(shell echo $(SIM) | tr A-Z a-z)),)
all::
	@echo "skipping simulator $(SIM) because it might not support SV interfaces"	
clean::
else
include $(shell cocotb-config --makefiles)/Makefile.sim
endif
