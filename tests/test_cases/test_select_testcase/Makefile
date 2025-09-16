# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

# select only y_tests from all MODULEs

include ../../designs/sample_module/Makefile

COCOTB_TEST_MODULES := x_tests,y_tests,y_tests_again
COCOTB_TESTCASE := y_test

# override PYTHONWARNINGS to prevent DeprecationWarning causing an error with use of COCOTB_TESTCASE
ifdef PYTHONWARNINGS
override PYTHONWARNINGS += ignore::DeprecationWarning:cocotb._init,
endif
