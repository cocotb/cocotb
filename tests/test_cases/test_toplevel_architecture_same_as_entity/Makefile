# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= vhdl
COCOTB_TOPLEVEL := test
VHDL_SOURCES := test.vhdl
COCOTB_TEST_MODULES := test_toplevel_architecture_same_as_entity

ifneq ($(filter $(SIM),ius xcelium),)
COMPILE_ARGS += -v93
endif

ifneq ($(shell echo $(TOPLEVEL_LANG) | tr A-Z a-z),vhdl)
all:
	@echo "Skipping test since only VHDL is supported"
clean::
else
include $(shell cocotb-config --makefiles)/Makefile.sim
endif
