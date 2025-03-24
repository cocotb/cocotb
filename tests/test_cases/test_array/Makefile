# Copyright cocotb contributors
# Copyright (c) 2016 Potential Ventures Ltd
# Copyright (c) 2016 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

# Icarus doesn't support structs (gh-2592)
# Verilator doesn't support structs (gh-1275)

ifeq ($(SIM),)
all:
	@echo "Skipping test_array since icarus doesn't support structs"

clean::
# nothing to clean, just define target in this branch

else ifneq ($(filter $(shell echo $(SIM) | tr A-Z a-z),icarus verilator),)
all:
	@echo "Skipping test_array since $(SIM) doesn't support structs"

clean::
# nothing to clean, just define target in this branch

else

include ../../designs/array_module/Makefile

COCOTB_TEST_MODULES = test_array

endif
