# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

ifeq ($(SIM),verilator)

all:
	@echo "Skipping test due to Verilator hanging when prematurely shutting down"  # gh-2008
clean::

else

include ../../designs/sample_module/Makefile

MODULE = issue_1279

endif
