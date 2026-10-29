# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

ifeq ($(SIM)_$(TOPLEVEL_LANG),questa_vhdl)

PROJ_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

VHDL_SOURCES := $(PROJ_DIR)/mylib.vhd
COCOTB_TOPLEVEL := myentity
TOPLEVEL_LIBRARY := mylib

COCOTB_TEST_MODULES := test_myentity

include $(shell cocotb-config --makefiles)/Makefile.sim

else

all:
	@echo "Skipping test because TOPLEVEL_LIBRARY is only supported in Questa in VHDL regressions."

endif
