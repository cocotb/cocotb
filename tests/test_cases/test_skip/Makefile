# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

COCOTB_TEST_MODULES := test_skip

# Ensure we had the correct number of skips and their reasons were preserved.
.PHONY: override_for_this_test
override_for_this_test:
	$(MAKE) all
	test $$(grep -o '<skipped[^>]*/>' $(COCOTB_RESULTS_FILE) | wc -l) -eq 4
	test $$(grep -o '<skipped[^>]*message="This test is skipped"' $(COCOTB_RESULTS_FILE) | wc -l) -eq 3
	test $$(grep -o '<skipped[^>]*message="Test was skipped"' $(COCOTB_RESULTS_FILE) | wc -l) -eq 1

include ../../designs/sample_module/Makefile
