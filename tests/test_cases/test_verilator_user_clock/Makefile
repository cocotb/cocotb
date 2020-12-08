# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog

ifneq ($(TOPLEVEL_LANG),verilog)

all:
	@echo "Skipping test due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being verilog"

clean::
# nothing to clean, just define target in this branch

else ifneq ($(shell echo $(SIM) | tr A-Z a-z),verilator)
all:
	@echo "Skipping test_verilator_user_clock due to SIM=$(SIM) not being verilator"

clean::
# nothing to clean, just define target in this branch

else


PWD=$(shell pwd)

VERILOG_SOURCES = $(PWD)/dual_clock.sv

TOPLEVEL = dual_clock
MODULE = test_verilator_user_clock
VERILATOR_USRCLK_FILE = verilator_usrclk.cpp

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
