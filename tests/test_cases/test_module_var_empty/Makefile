# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

# test MODULE is empty
# should cause regression initialization failure so no results.xml is written

MODULE := " "

.PHONY: override_for_this_test
override_for_this_test:
	-$(MAKE) all
	@test ! -f $(COCOTB_RESULTS_FILE)

include ../../designs/sample_module/Makefile
