# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

COCOTB_TEST_MODULES := test_verilator_timing_c
EXTRA_ARGS := "--timing"

include ../../designs/verilator_timing/Makefile

ifneq ($(shell ./check_version 2>/dev/null 1>&2; echo $$?),0)
all:
	@echo "Skipping test since it requires newer version of cocotb"
else ifneq ($(shell echo $(TOPLEVEL_LANG) | tr A-Z a-z),verilog)
all:
	@echo "Skipping test since only Verilog is supported"
else ifeq ($(filter verilator,$(shell echo $(SIM) | tr A-Z a-z)),)
all:
	@echo "Skipping test since only Verilator is supported"
else
include $(shell cocotb-config --makefiles)/Makefile.sim
endif
