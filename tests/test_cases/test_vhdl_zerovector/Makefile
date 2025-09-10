# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

ifeq ($(TOPLEVEL_LANG),vhdl)

ifneq ($(filter $(SIM),ius xcelium),)
    COMPILE_ARGS += -v93
endif

COCOTB_TOPLEVEL := vhdl_zerovector
COCOTB_TEST_MODULES := test_vhdl_zerovector
VHDL_SOURCES := vhdl_zerovector.vhdl

# cocotb inclusions
include $(shell cocotb-config --makefiles)/Makefile.sim

else
all:
	$(info Skipping simulation as only TOPLEVEL_LANG=vhdl is supported)

clean::

endif
