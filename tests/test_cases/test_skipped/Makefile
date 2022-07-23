# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

include ../../designs/sample_module/Makefile

SKIPPED_TEST_FILE = ran_skipped_test~

clean::
	$(RM) -r ${SKIPPED_TEST_FILE}

# Override the default target. We need to run clean (to remove the cached test file)
# and then test to make sure it is recreated.
.DEFAULT_GOAL := override
.PHONY: override
override: clean all
	 @test -f $(SKIPPED_TEST_FILE) || (echo "ERROR: skip=True test was not ran!" >&2 && exit 1)

# Set TESTCASE; run test_skipped even though skip=True is set.
TESTCASE = test_skipped

MODULE = test_skipped
