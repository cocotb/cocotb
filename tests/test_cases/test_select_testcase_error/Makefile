# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

# This module exists, but...
COCOTB_TEST_MODULES := x_tests
# ...this test does not exist
TESTCASE := y_test

# TESTCASE filtering out all tests results in a warning

# override PYTHONWARNINGS to prevent DeprecationWarning causing an error with use of COCOTB_TESTCASE
ifdef PYTHONWARNINGS
override PYTHONWARNINGS := $(PYTHONWARNINGS),ignore::DeprecationWarning:cocotb.regression
endif

include ../../designs/sample_module/Makefile
