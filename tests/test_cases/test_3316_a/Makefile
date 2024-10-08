# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
TOPLEVEL_LANG ?= verilog
SIM ?= verilator
COCOTB_TEST_MODULES := test_3316_a
VERILOG_SOURCES := ../test_3316/test_3316.sv
COCOTB_TOPLEVEL := test_3316

ifneq ($(shell echo $(TOPLEVEL_LANG) | tr A-Z a-z),verilog)
all:
	@echo "Skipping test since only Verilog is supported"
else ifeq ($(filter verilator,$(shell echo $(SIM) | tr A-Z a-z)),)
all:
	@echo "Skipping test since only Verilator is supported"
else
all: timing no-timing
endif

MAKE_ARGS = TOPLEVEL_LANG=$(TOPLEVEL_LANG) \
			SIM=$(SIM) \
			COCOTB_TEST_MODULES=$(COCOTB_TEST_MODULES) \
			VERILOG_SOURCES="$(VERILOG_SOURCES)" \
			COCOTB_TOPLEVEL=$(COCOTB_TOPLEVEL) \
			EXTRA_ARGS=$(EXTRA_ARGS)

timing: EXTRA_ARGS="--timing"
timing:
	$(MAKE) -f $(shell cocotb-config --makefiles)/Makefile.sim $(MAKE_ARGS)

no-timing: EXTRA_ARGS="--no-timing"
no-timing:
	$(MAKE) -f $(shell cocotb-config --makefiles)/Makefile.sim $(MAKE_ARGS)
