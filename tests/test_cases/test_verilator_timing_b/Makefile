# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
COCOTB_TEST_MODULES := test_verilator_timing_b
EXTRA_ARGS := "+define+TEST_CLK_EXTERNAL=1"

include ../../designs/verilator_timing/Makefile

ifneq ($(shell echo $(TOPLEVEL_LANG) | tr A-Z a-z),verilog)
all:
	@echo "Skipping test since only Verilog is supported"
else ifeq ($(filter verilator,$(shell echo $(SIM) | tr A-Z a-z)),)
all:
	@echo "Skipping test since only Verilator is supported"
else
include $(shell cocotb-config --makefiles)/Makefile.sim
endif
