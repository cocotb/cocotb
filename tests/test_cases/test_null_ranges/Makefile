# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

ifeq ($(TOPLEVEL_LANG),vhdl)

ifneq ($(filter $(SIM),ius xcelium),)
    COMPILE_ARGS += -v93
endif

COCOTB_TOPLEVEL := null_ranges_top
COCOTB_TEST_MODULES := test_null_ranges
VHDL_SOURCES := null_ranges_pkg.vhdl null_ranges.vhdl

# cocotb inclusions
include $(shell cocotb-config --makefiles)/Makefile.sim

else
all:
	$(info Skipping simulation as only TOPLEVEL_LANG=vhdl is supported)

clean::

endif
