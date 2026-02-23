# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
COCOTB_TEST_MODULES := test_verilator_timing_a

include ../../designs/verilator_timing/Makefile

ifneq ($(shell echo $(TOPLEVEL_LANG) | tr A-Z a-z),verilog)
all:
	@echo "Skipping test since only Verilog is supported"
else ifeq ($(filter verilator,$(shell echo $(SIM) | tr A-Z a-z)),)
all:
	@echo "Skipping test since only Verilator is supported"
else

.PHONY: override_for_this_test
override_for_this_test:
	# We cannot normally rely on the simulator return code, but this test is specific to Verilator
	if $(MAKE) all; then echo "Expected test to fail without --timing flag"; false; else echo "Failed as expected"; fi

include $(shell cocotb-config --makefiles)/Makefile.sim
endif
