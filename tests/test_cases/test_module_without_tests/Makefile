# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

# test COCOTB_TEST_MODULES is set
# should cause regression initialization failure so no results.xml is written

COCOTB_TEST_MODULES=test_nothing

.PHONY: override_for_this_test
override_for_this_test:
	-$(MAKE) all
	@test ! -f $(COCOTB_RESULTS_FILE)

include ../../designs/sample_module/Makefile
