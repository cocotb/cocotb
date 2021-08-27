# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

MODULE := test_forked_exception

# ensure the test runs, squash any error code, and ensure a failing test was reported
.PHONY: override_for_this_test
override_for_this_test:
	-$(MAKE) all
	@test ! -f $(COCOTB_RESULTS_FILE)

include ../../designs/sample_module/Makefile
