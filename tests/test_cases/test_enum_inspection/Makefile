# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
#
# Prototype: probe each simulator's VPI type-inspection coverage for typed
# enums. A small C++ library (enum_inspector.cpp) is loaded via the GPI_USERS
# mechanism and uses raw VPI calls (vpiTypespec / vpiBaseTypespec /
# vpiEnumConst) to dump everything it finds to enum_inspection.log. The
# regression then diffs against expected_results.log.
#
# This test runs only for Verilog tops on VPI-capable simulators (Icarus,
# Verilator, Questa, Riviera, Xcelium, VCS). VHDL simulators are skipped.

TOPLEVEL_LANG ?= verilog

# Only Verilog tops on VPI-capable sims are interesting here. Skip otherwise.
SUPPORTED_SIMS := icarus verilator questa riviera xcelium vcs
SIM ?= icarus

ifneq ($(TOPLEVEL_LANG),verilog)

all:
	@echo "Skipping test_enum_inspection: TOPLEVEL_LANG=$(TOPLEVEL_LANG) (verilog only)"
clean::
	@:

else ifeq ($(filter $(SIM),$(SUPPORTED_SIMS)),)

all:
	@echo "Skipping test_enum_inspection: SIM=$(SIM) not in $(SUPPORTED_SIMS)"
clean::
	@:

else

PWD := $(shell pwd)

# tests/Makefile invokes us with no args. Force the categorization wrapper
# to be the default goal regardless of what targets the included
# Makefile.sim or our own .so build rule register first.
.DEFAULT_GOAL := override_for_this_test

VERILOG_SOURCES = $(PWD)/enums.sv
COCOTB_TOPLEVEL = top

# Build the inspector .so. The vendored VPI headers live in the source tree
# at src/cocotb/_vendor/vpi/ -- we point straight there rather than at the
# installed package, because some build modes (wheel installs in CI nox
# envs) don't bundle the headers under site-packages/cocotb/_vendor.
REPO_ROOT := $(PWD)/../../..
VPI_HEADERS_DIR := $(REPO_ROOT)/src/cocotb/_vendor/vpi

CXX ?= g++
INSPECTOR_LIB := $(PWD)/libenum_inspector.so

# -fPIC for shared, -shared output; allow unresolved vpi_* (the simulator
# provides them at runtime). The flag to tell the linker to tolerate
# unresolved symbols differs between GNU ld (Linux) and Apple ld (macOS).
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
ALLOW_UNRESOLVED := -Wl,-undefined,dynamic_lookup
else
ALLOW_UNRESOLVED := -Wl,--unresolved-symbols=ignore-all
endif

$(INSPECTOR_LIB): $(PWD)/enum_inspector.cpp
	$(CXX) -std=c++17 -O0 -g -fPIC -shared \
		-I$(VPI_HEADERS_DIR) \
		$(ALLOW_UNRESOLVED) \
		-o $@ $<

# GPI_USERS = only our inspector. We do NOT include libpython + pygpi -- this
# test is pure VPI, no cocotb Python side.
GPI_USERS := $(INSPECTOR_LIB),enum_inspector_entry
export GPI_USERS

# Always exit 0 -- the table is the deliverable, not pass/fail.
.PHONY: override_for_this_test
override_for_this_test: $(INSPECTOR_LIB)
	@rm -f enum_inspection.log
	-$(MAKE) sim
	@python compare_log.py enum_inspection.log

include $(shell cocotb-config --makefiles)/Makefile.sim

clean::
	rm -f $(INSPECTOR_LIB) enum_inspection.log

endif
