# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
SIM ?= ghdl
TOPLEVEL_LANG ?= vhdl
VHDL_SOURCES_blib := b.vhdl
VHDL_SOURCES := a.vhdl
COCOTB_TOPLEVEL := a
COCOTB_TEST_MODULES := test_ab

ifneq ($(filter $(SIM),xcelium),)
    COMPILE_ARGS += -v93
endif

ifneq ($(filter nvc questa-compat questa-qisqrun modelsim xcelium ius riviera,$(shell echo $(SIM) | tr A-Z a-z)),)
    VHDL_LIB_ORDER := blib
endif

ifneq ($(shell echo $(TOPLEVEL_LANG) | tr A-Z a-z),vhdl)
all:
	@echo "Skipping test since only VHDL is supported"
clean::
else ifeq ($(filter ghdl nvc questa-compat questa-qisqrun modelsim xcelium ius riviera,$(shell echo $(SIM) | tr A-Z a-z)),)
all:
	@echo "Skipping test since only GHDL, NVC, Questa/ModelSim, Xcelium, Incisive and Riviera-PRO are supported"
clean::
else
include $(shell cocotb-config --makefiles)/Makefile.sim
endif
