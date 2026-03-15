# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

COCOTB_TEST_MODULES := test_listing_1,test_listing_2
export COCOTB_LIST_TESTS := 1

ifneq ($(filter riviera questa,$(SIM)),)

all:
	@echo "Riviera and Questa are not supported on this test, skipping."

else

.PHONY: override
override:
	rm -f sim.log
	-$(MAKE) all 2>/dev/null | tee sim.log
	python check_results.py sim.log

include ../../designs/sample_module/Makefile

endif
