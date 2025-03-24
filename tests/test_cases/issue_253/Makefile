# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

ifneq ($(SIM),)
all:
	@echo "Skipping issue_253 only runs on icarus"
else

include ../../designs/sample_module/Makefile

COCOTB_TEST_MODULES = issue_253

# Redefine the Icarus rule for results.xml to not specify TOPLEVEL, test should still pass

all: empty_top_level no_top_level notset_top_level

$(COCOTB_RESULTS_FILE):
	@echo "Skipping"

notset_top_level: $(SIM_BUILD)/sim.vvp $(CUSTOM_SIM_DEPS)
	COCOTB_TEST_MODULES=$(COCOTB_TEST_MODULES) \
	COCOTB_TEST_FILTER=issue_253_notset TOPLEVEL= \
	vvp -M $(shell cocotb-config --lib-dir) -m $(shell cocotb-config --lib-name vpi icarus) $(SIM_BUILD)/sim.vvp $(SIM_ARGS) $(EXTRA_ARGS) $(PLUSARGS)
	mkdir -p $@_result && mv results.xml $@_result/

empty_top_level: $(SIM_BUILD)/sim.vvp $(CUSTOM_SIM_DEPS)
	COCOTB_TEST_MODULES=$(COCOTB_TEST_MODULES) \
	COCOTB_TEST_FILTER=issue_253_empty TOPLEVEL="" \
	vvp -M $(shell cocotb-config --lib-dir) -m $(shell cocotb-config --lib-name vpi icarus) $(SIM_BUILD)/sim.vvp $(SIM_ARGS) $(EXTRA_ARGS) $(PLUSARGS)
	mkdir -p $@_result && mv results.xml $@_result/

no_top_level: $(SIM_BUILD)/sim.vvp $(CUSTOM_SIM_DEPS)
	COCOTB_TEST_MODULES=$(COCOTB_TEST_MODULES) \
	COCOTB_TEST_FILTER=issue_253_none \
	vvp -M $(shell cocotb-config --lib-dir) -m $(shell cocotb-config --lib-name vpi icarus) $(SIM_BUILD)/sim.vvp $(SIM_ARGS) $(EXTRA_ARGS) $(PLUSARGS)
	mkdir -p $@_result && mv results.xml $@_result/

endif

clean::
	$(RM) -r empty_top_level_result
	$(RM) -r no_top_level_result
	$(RM) -r notset_top_level_result
