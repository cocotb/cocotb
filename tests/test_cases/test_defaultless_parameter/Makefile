# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

ifeq ($(SIM),)
USING_ICARUS := 1
endif

ifeq ($(shell echo $(SIM) | tr A-Z a-z),icarus)
USING_ICARUS := 1
endif

ifneq ($(USING_ICARUS),)
ICARUS_MIN := 12.0
ICARUS_VERSION := $(shell iverilog -V 2>/dev/null | head -n1 | cut -d ' ' -f 4)
MIN_VERSION := $(shell printf "%s\n%s\n" "$(ICARUS_MIN)" "$(ICARUS_VERSION)" | sort -g | head -1)
ifneq ($(MIN_VERSION),$(ICARUS_MIN))
SKIP := 1
$(info "Skipping test_defaultless_parameter since icarus < v12.0 doesn't support defaultless parameters")
endif
endif

TOPLEVEL_LANG ?= verilog
ifneq ($(TOPLEVEL_LANG),verilog)
SKIP := 1
$(info "Skipping . . . Verilog only")
endif

ifeq ($(SKIP),)

VERILOG_SOURCES = $(PWD)/test_defaultless_parameter.sv
# Needed for defaultless parameter support in Xcelium
export CADENCE_ENABLE_AVSREQ_44905_PHASE_1=1
COCOTB_TOPLEVEL := cocotb_defaultless_parameter
COCOTB_TEST_MODULES = test_defaultless_parameter

include $(shell cocotb-config --makefiles)/Makefile.sim

else

all:
	@echo "Skipping test_defaultless_parameter"

clean::
# nothing to clean, just define target in this branch

endif
