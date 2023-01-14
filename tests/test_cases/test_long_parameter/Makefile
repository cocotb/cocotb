# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

COMPILE_ARGS += -Psample_module.INT_PARAM=10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
MODULE = test_long_parameter

ifeq ($(SIM),)
include ../../designs/sample_module/Makefile

else ifeq ($(shell echo $(SIM) | tr A-Z a-z),icarus)
include ../../designs/sample_module/Makefile

else
all:
	@echo "Skipping test_long_parameter since only icarus supports long parameters"
clean::
endif
