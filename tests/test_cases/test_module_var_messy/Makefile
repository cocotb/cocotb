# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

# test MODULE contains leading and trailing separators
# should cause regression initialization failure so no results.xml is written

MODULE=" , test_nothing  ,"

.PHONY: override_for_this_test
override_for_this_test:
	-$(MAKE) all
	@test ! -f $(COCOTB_RESULTS_FILE)

include ../../designs/sample_module/Makefile
