# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
SIM ?= ghdl
TOPLEVEL_LANG ?= vhdl

VHDL_SOURCES_blib := b.vhdl
VHDL_SOURCES_clib := c.vhdl
VHDL_SOURCES_dlib := d.vhdl
VHDL_SOURCES_elib := e.vhdl

VHDL_SOURCES := a.vhdl
COCOTB_TOPLEVEL := a
COCOTB_TEST_MODULES := test_abcde

ifneq ($(filter $(SIM),xcelium),)
    COMPILE_ARGS += -v93
endif

ifneq ($(filter nvc questa-compat questa-qisqrun modelsim xcelium riviera,$(shell echo $(SIM) | tr A-Z a-z)),)
    VHDL_LIB_ORDER := elib dlib clib blib
endif

ifneq ($(shell echo $(TOPLEVEL_LANG) | tr A-Z a-z),vhdl)
all:
	@echo "Skipping test since only VHDL is supported"
clean::
else ifeq ($(filter ghdl nvc questa-compat questa-qisqrun modelsim xcelium riviera,$(shell echo $(SIM) | tr A-Z a-z)),)
all:
	@echo "Skipping test since only GHDL, NVC, Questa/ModelSim, Xcelium and Riviera-PRO are supported"
clean::
else
include $(shell cocotb-config --makefiles)/Makefile.sim
endif
