# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

ifeq ($(SIM),questa)

PROJ_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

VHDL_SOURCES_mylib := $(PROJ_DIR)/mylib.vhd
VHDL_LIB_ORDER := mylib

TOPLEVEL := myentity
TOPLEVEL_LIBRARY := mylib
TOPLEVEL_LANG := vhdl

MODULE := test_myentity

include $(shell cocotb-config --makefiles)/Makefile.sim

else

all:
	@echo "Skipping test because TOPLEVEL_LIBRARY is only supported in Questa."

endif
