# Copyright cocotb contributors
# Copyright (c) 2015 Potential Ventures Ltd
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

ifeq ($(shell echo $(SIM) | tr A-Z a-z),riviera)
all:
	@echo "Skipping test_iteration_mixedlang since Riviera-PRO crashes (see https://github.com/cocotb/cocotb/issues/3293)"
clean::

else

include ../../designs/uart2bus/Makefile
COCOTB_TEST_MODULES = test_iteration
endif
