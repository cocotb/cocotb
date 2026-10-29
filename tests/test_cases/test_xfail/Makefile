# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

COCOTB_TEST_MODULES := test_xfail

# Ensure the correct number of tests ran.
# Maybe one day we can explicitly check for XFAIL.
.PHONY: override_for_this_test
override_for_this_test:
	$(MAKE) all
	python -m cocotb_tools.combine_results | grep -q "Ran a total .* 11 TestCases"

include ../../designs/sample_module/Makefile
