# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

TOPLEVEL_LANG = verilog
VERILOG_SOURCES = $(shell pwd)/digital.sv
TOPLEVEL = digital

MODULE = test_analog_model

ifneq ($(filter $(SIM),ius xcelium),)
    SIM_ARGS += -unbuffered
endif

include $(shell cocotb-config --makefiles)/Makefile.sim
