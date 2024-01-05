# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog
ifneq ($(TOPLEVEL_LANG),verilog)
SKIP := 1
$(info "Skipping . . . Verilog only")
endif

ifeq ($(SKIP),)

VERILOG_SOURCES = test_initial.sv
TOPLEVEL := cocotb_initial
MODULE = test_initial

include $(shell cocotb-config --makefiles)/Makefile.sim

else

all:
	@echo "Skipping test_initial"

clean::
# nothing to clean, just define target in this branch

endif
