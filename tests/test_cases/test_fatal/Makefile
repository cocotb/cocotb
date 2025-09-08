# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog
COCOTB_TOPLEVEL := fatal
COCOTB_TEST_MODULES := test_fatal

PWD=$(shell pwd)

ifeq ($(TOPLEVEL_LANG),verilog)
    VERILOG_SOURCES := $(PWD)/fatal.sv
else ifeq ($(TOPLEVEL_LANG),vhdl)
    VHDL_SOURCES := $(PWD)/fatal.vhd
    ifneq ($(filter $(SIM),ius xcelium),)
        COMPILE_ARGS += -v93
    endif
endif

ifeq ($(shell echo $(SIM) | tr A-Z a-z),verilator)
    COMPILE_ARGS += --timing
endif

SKIP := 0
ifeq ($(SIM),riviera)
  # Determine the version of Riviera-PRO being used.
  # Assume "python3" to be available, the exact version does not matter much
  # in this context.
  RIVIERA_VERSION_INT := $(shell vsimsa -version | python3 -c 'import re,sys; m=re.match(r".+version (\d+)\.(\d+).+", sys.stdin.read()); print(f"{int(m[1])*100+int(m[2])}")')

  ifeq ($(shell test $(RIVIERA_VERSION_INT) -lt 202404; echo $$?),0)
    $(info Skipping test for Riviera-PRO versions < 2024.04 due to a shutdown hang)
    SKIP := 1
  endif
endif

ifeq ($(SKIP),1)
all:
	@echo "Skipping test"
clean::

else
# squash error code from simulator and ensure the cocotb test passed
.PHONY: override_for_this_test
override_for_this_test:
	-$(MAKE) all
	$(call check_for_results_file)
	python -m cocotb_tools.combine_results &> /dev/null

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
