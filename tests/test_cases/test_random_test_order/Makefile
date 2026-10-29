# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

COCOTB_TEST_MODULES = test_random_test_order

# This particular seed value provides a nice spread of how random the test order can be.
#
# Specifically, it demonstrates that:
#	- Tests within a stage are shuffled.
#	- The ordering of stages is upheld.
# 	- Parametrized tests are shuffled among the stage.
export COCOTB_RANDOM_SEED := 1233

# Set COCOTB_RANDOM_TEST_ORDER to randomize tests within stages.
export COCOTB_RANDOM_TEST_ORDER := 1

include ../../designs/sample_module/Makefile
