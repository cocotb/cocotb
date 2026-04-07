# Copyright cocotb contributors
# Copyright (c) 2015 Potential Ventures Ltd
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

# detecting an expected failure has to happen here, as the python code is invalid
.PHONY: override_for_this_test
override_for_this_test:
	if $(MAKE) all; then echo "Expected this to fail"; false; else echo "Failed as expected"; fi

include ../../designs/sample_module/Makefile

COCOTB_TEST_MODULES = test_simple
unexport GPI_USERS
