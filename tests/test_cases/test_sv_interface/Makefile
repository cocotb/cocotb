# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

TOPLEVEL_LANG ?= verilog
VERILOG_SOURCES = $(shell pwd)/top.sv
MODULE = test_sv_if
TOPLEVEL = top

ifneq ($(shell echo $(SIM) | tr A-Z a-z),verilator)
all::
clean::
else
include $(shell cocotb-config --makefiles)/Makefile.sim
endif
