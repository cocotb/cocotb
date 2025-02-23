# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

TOPLEVEL_LANG ?= verilog
SIM ?= icarus

PWD=$(shell pwd)

# SystemVerilog parameters
DATA_WIDTH ?= 8

VERILOG_SOURCES = $(PWD)/../hdl/dff8.sv

# Set module parameters
ifeq ($(SIM),icarus)
	COMPILE_ARGS += -Pdff8.DATA_WIDTH=$(DATA_WIDTH)
else ifneq ($(filter $(SIM),questa modelsim riviera activehdl),)
	SIM_ARGS += -gDATA_WIDTH=$(DATA_WIDTH)
else ifeq ($(SIM),vcs)
	COMPILE_ARGS += -pvalue+dff8/DATA_WIDTH=$(DATA_WIDTH)
else ifeq ($(SIM),verilator)
	COMPILE_ARGS += -GDATA_WIDTH=$(DATA_WIDTH)
else ifneq ($(filter $(SIM),ius xcelium),)
	EXTRA_ARGS += -defparam "dff8.DATA_WIDTH=$(DATA_WIDTH)"
endif

ifneq ($(filter $(SIM),riviera activehdl),)
	COMPILE_ARGS += -sv2k12
endif


# Fix the seed to ensure deterministic tests
export RANDOM_SEED := 123456789

TOPLEVEL    := dff8
MODULE      := test_dff8

include $(shell cocotb-config --makefiles)/Makefile.sim

# Profiling

DOT_BINARY ?= dot

test_profile.pstat: sim

callgraph.svg: test_profile.pstat
	$(shell cocotb-config --python-bin) -m gprof2dot -f pstats ./$< | $(DOT_BINARY) -Tsvg -o $@

.PHONY: profile
profile:
	COCOTB_ENABLE_PROFILING=1 $(MAKE) callgraph.svg
