# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

ifeq ($(SIM),ghdl)

all:
	@echo Skipping test because GHDL does not support identifiers longer than 1023 characters.
	@echo See also https://github.com/ghdl/ghdl/issues/1930

else

PROJ_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

TOPLEVEL_LANG ?= verilog

ifeq ($(TOPLEVEL_LANG),verilog)
VERILOG_SOURCES := $(PROJ_DIR)/test.sv
else ifeq ($(TOPLEVEL_LANG),vhdl)
VHDL_SOURCES := $(PROJ_DIR)/test.vhd
endif

TOPLEVEL := test

export MODULE := test_long_log_msg
export COCOTB_LOG_LEVEL := DEBUG

.PHONY: override_for_this_test
override_for_this_test:
	$(MAKE) all 2>errlog
	! grep &>/dev/null "Log message construction failed" errlog

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
