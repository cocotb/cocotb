# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

MODULE := test_failure

# ensure the test runs, squash any error code, and ensure a failing test was reported
.PHONY: override_for_this_test
override_for_this_test:
	-$(MAKE) all
	$(call check_for_results_file)
	test $$(../../../bin/combine_results.py | grep "Failure in testsuite" | wc -l) -eq 4 && rm -f results.xml

include ../../designs/sample_module/Makefile
