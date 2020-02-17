###############################################################################
# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
###############################################################################

TOPLEVEL_LANG ?= verilog
COCOTB_BFM_MODULES += rv_bfms

ifneq ($(TOPLEVEL_LANG),verilog)

all:
	@echo "Skipping test due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being verilog"
clean::

else

ifeq ($(OS),Msys)
WPWD=$(shell sh -c 'pwd -W')
else
WPWD=$(shell pwd)
endif

COCOTB?=$(WPWD)/../../..

VERILOG_SOURCES = $(COCOTB)/tests/designs/rv_bfm/rv_bfm_top.sv
TOPLEVEL = rv_bfm_top

MODULE = bfm_test

include $(COCOTB)/makefiles/Makefile.inc
include $(COCOTB)/makefiles/Makefile.sim

endif
