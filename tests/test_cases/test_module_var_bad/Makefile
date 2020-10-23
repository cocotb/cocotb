# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

# should cause a failure in cocotb._initialize_testbench which will trigger a path in
# cocotb._sim_event that isn't otherwise seen
MODULE := bad

.PHONY: override_for_this_test
override_for_this_test:
	if $(MAKE) all; then echo "Expected this to fail"; false; else echo "Failed as expected"; fi

include ../../designs/sample_module/Makefile
