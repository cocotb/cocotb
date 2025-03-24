# Copyright cocotb contributors
# Copyright (c) 2015 Potential Ventures Ltd
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= vhdl

ifneq ($(TOPLEVEL_LANG),vhdl)

all:
	@echo "Skipping test due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being vhdl"
clean::

else

COCOTB_TOPLEVEL = dec_viterbi_ent

PWD=$(shell pwd)

COCOTB?=$(PWD)/../../..

SRC_BASE = $(COCOTB)/tests/designs/viterbi_decoder_axi4s

RTL_LIBRARY = dec_viterbi

VHDL_SOURCES = $(SRC_BASE)/packages/pkg_helper.vhd \
	       $(SRC_BASE)/packages/pkg_param.vhd \
	       $(SRC_BASE)/packages/pkg_param_derived.vhd \
	       $(SRC_BASE)/packages/pkg_types.vhd \
	       $(SRC_BASE)/packages/pkg_components.vhd \
	       $(SRC_BASE)/packages/pkg_trellis.vhd \
	       $(SRC_BASE)/src/generic_sp_ram.vhd \
	       $(SRC_BASE)/src/axi4s_buffer.vhd \
	       $(SRC_BASE)/src/branch_distance.vhd \
	       $(SRC_BASE)/src/traceback.vhd \
	       $(SRC_BASE)/src/acs.vhd \
	       $(SRC_BASE)/src/ram_ctrl.vhd \
	       $(SRC_BASE)/src/reorder.vhd \
	       $(SRC_BASE)/src/recursion.vhd \
	       $(SRC_BASE)/src/dec_viterbi.vhd

ifneq ($(filter $(SIM),ius xcelium),)
    COMPILE_ARGS += -v93
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
