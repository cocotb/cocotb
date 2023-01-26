# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= verilog

ifneq ($(TOPLEVEL_LANG),verilog)

all:
	@echo "Skipping test due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being verilog"
clean::

else

VERILOG_INCLUDE_DIRS = \
	./common \
	./const_stream
VERILOG_SOURCES = simple_and.sv
TOPLEVEL = simple_and
MODULE = test_verilog_include_dirs

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
