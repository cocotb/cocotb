# Copyright cocotb contributors
# Copyright (c) 2015 Potential Ventures Ltd
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

# Detect the expected GPI implementation loading failure in Make.
.PHONY: override_for_this_test
override_for_this_test:
	if $(MAKE) all; then echo "Expected this to fail"; false; else echo "Failed as expected"; fi

include ../../designs/sample_module/Makefile

COCOTB_TEST_MODULES = test_simple

# Simulator Makefiles provide their required GPI_IMPL inline. Override it at
# the command boundary so this test still exercises an invalid implementation.
override SIM_CMD_PREFIX := GPI_IMPL=invalid $(SIM_CMD_PREFIX)
