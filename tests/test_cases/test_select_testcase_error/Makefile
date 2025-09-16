# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

# This module exists, but...
COCOTB_TEST_MODULES := x_tests
# ...this test does not exist
TESTCASE := y_test

# TESTCASE filtering out all tests results in a warning

include ../../designs/sample_module/Makefile

# override PYTHONWARNINGS to prevent DeprecationWarning causing an error with use of TESTCASE
ifdef PYTHONWARNINGS
override PYTHONWARNINGS += ignore::DeprecationWarning:cocotb._init,
endif
