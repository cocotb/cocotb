# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog
SIM ?= icarus
COCOTB_TEST_MODULES = test_cocotb_tops
VERILOG_SOURCES = tops.v
COCOTB_TOPLEVEL = verilog_top_a
COCOTB_TOPLEVEL += verilog_top_b


ifneq (,$(filter icarus,$(SIM)))

include $(shell cocotb-config --makefiles)/Makefile.sim

else

skip_unsupported_simulators:
	@echo "Current supported simulators for feature multiple tops = Icarus"

endif
