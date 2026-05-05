# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

COCOTB_TEST_MODULES := test_skip

# Ensure we had the correct number of skips
.PHONY: override_for_this_test
override_for_this_test:
	$(MAKE) all
	test $$(grep '<skipped.*/>' $(COCOTB_RESULTS_FILE) | wc -l) -eq 4

include ../../designs/sample_module/Makefile
