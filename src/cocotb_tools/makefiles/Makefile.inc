# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

# Common makefile included by everything

ifndef COCOTB_MAKEFILE_INC_INCLUDED # Protect against multiple includes
COCOTB_MAKEFILE_INC_INCLUDED = 1

# Default sim rule will force a re-run of the simulation (though the cocotb library
# and RTL compilation phases are still evaluated by makefile dependencies)
.PHONY: sim
sim:
	$(RM) $(COCOTB_RESULTS_FILE)
	"$(MAKE)" -f $(firstword $(MAKEFILE_LIST)) $(COCOTB_RESULTS_FILE)

# Make sure to use bash for the pipefail option used in many simulator Makefiles
SHELL := bash

OS=$(shell uname)
ifneq (, $(findstring MINGW, $(OS)))
    OS := Msys
else ifneq (, $(findstring MSYS, $(OS)))
    OS := Msys
endif
export OS

export PYGPI_PYTHON_BIN := $(shell $(PYTHON_BIN) -m cocotb_tools.config --python-bin)

# Directory containing the cocotb Makefiles
COCOTB_MAKEFILES_DIR := $(shell $(PYTHON_BIN) -m cocotb_tools.config --makefiles)

include $(COCOTB_MAKEFILES_DIR)/Makefile.deprecations

PYTHON_ARCH := $(shell $(PYTHON_BIN) -c 'from platform import architecture; print(architecture()[0])')
ifeq ($(filter $(PYTHON_ARCH),64bit 32bit),)
    $(error Unknown Python architecture: $(PYTHON_ARCH))
endif

ifeq ($(OS),Msys)
    to_tcl_path = $(shell cygpath -m $(1) )
else
    to_tcl_path = $(1)
endif

# Check that the COCOTB_RESULTS_FILE was created, since we can't set an exit code from cocotb.
define check_for_results_file
    @test -f $(COCOTB_RESULTS_FILE) || (echo "ERROR: $(COCOTB_RESULTS_FILE) was not written by the simulation!" >&2 && exit 1)
endef

# Check that the COCOTB_RESULTS_FILE was created and has no failures
define check_results
    @$(PYTHON_BIN) -m cocotb_tools.check_results $(COCOTB_RESULTS_FILE)
endef

SIM_BUILD ?= sim_build
export SIM_BUILD

COCOTB_RESULTS_FILE ?= results.xml
COCOTB_HDL_TIMEUNIT ?= 1ns
COCOTB_HDL_TIMEPRECISION ?= 1ps

export COCOTB_RESULTS_FILE


$(SIM_BUILD):
	mkdir -p $@

# Regression rule uses Make dependencies to determine whether to run the simulation
.PHONY: regression
regression: $(COCOTB_RESULTS_FILE)

# Attempt to detect TOPLEVEL_LANG based on available sources if not set
ifeq ($(TOPLEVEL_LANG),)

ifneq ($(VHDL_SOURCES),)
ifeq ($(VERILOG_SOURCES),)
	TOPLEVEL_LANG := vhdl
endif
else ifneq ($(VERILOG_SOURCES),)
ifeq ($(VHDL_SOURCES),)
	TOPLEVEL_LANG := verilog
endif
endif

endif

define find_libpython_errmsg =


find_libpython was not able to find a libpython in the current Python environment. Ensure
the Python development packages are installed. If they are installed and find_libpython
is not finding the path to libpython, file an upstream bug in find_libpython; then
manually override the LIBPYTHON_LOC make variable with the absolute path to libpython.so
(or python.dll on Windows).

endef

ifndef LIBPYTHON_LOC

# get the path to libpython and the return code from the script
# adapted from https://stackoverflow.com/a/24658961/6614127
FIND_LIBPYTHON_RES := $(shell $(PYTHON_BIN) -m cocotb_tools.config --libpython; echo $$?)
FIND_LIBPYTHON_RC := $(lastword $(FIND_LIBPYTHON_RES))
LIBPYTHON_LOC := $(strip $(subst $(FIND_LIBPYTHON_RC)QQQQ,,$(FIND_LIBPYTHON_RES)QQQQ))

# complain if libpython isn't found, and export otherwise
ifneq ($(FIND_LIBPYTHON_RC),0)
    $(error $(find_libpython_errmsg))
endif

endif

export LIBPYTHON_LOC

define check_vhdl_sources
if [ "$(VHDL_SOURCES_$(LIB))" == "" ]; then \
  >&2 echo "ERROR: VHDL_SOURCES_$(LIB) is empty or undefined, but '$(LIB)' is present in VHDL_LIB_ORDER."; \
  exit 1; \
fi;
endef

define check_lib_order
  if [ "$(filter $(SOURCES_VAR:VHDL_SOURCES_%=%), $(VHDL_LIB_ORDER))" == "" ]; then \
    >&2 echo "ERROR: $(SOURCES_VAR) defined, but library $(SOURCES_VAR:VHDL_SOURCES_%=%) not present in VHDL_LIB_ORDER."; \
    exit 1; \
  fi;
endef

# NOTE: if the following simulator list is modified, update the sentence
# "This flag is enabled by default for the GHDL, NVC and Verilator simulators."
# in docs/source/building.rst accordingly.
ifneq ($(filter $(SIM),nvc ghdl verilator),)
  COCOTB_TRUST_INERTIAL_WRITES ?= 1
else
  COCOTB_TRUST_INERTIAL_WRITES ?= 0
endif

export COCOTB_TRUST_INERTIAL_WRITES


# Universal
clean::
	@$(RM) -rf $(SIM_BUILD)
	@$(RM) -f $(COCOTB_RESULTS_FILE)


# Active-HDL
clean::
	@$(RM) -rf work
	@$(RM) -rf wave.asdb

# IUS
clean::
	@$(RM) -rf irun.*
	@$(RM) -rf ncsim.*
	@$(RM) -rf gdb_cmd_ncsim

# VCS
clean::
	@$(RM) -rf simv.daidir
	@$(RM) -rf cm.log
	@$(RM) -rf ucli.key

# Riviera
clean::
	@$(RM) -rf compile
	@$(RM) -rf library.cfg
	@$(RM) -rf dataset.asdb

# Verilator
clean::
	@$(RM) -f dump.vcd
	@$(RM) -f dump.fst

# Xcelium
clean::
	@$(RM) -rf xrun.*
	@$(RM) -rf xmsim.*
	@$(RM) -rf gdb_cmd_xmsim
	@$(RM) -f qrun*
	@$(RM) -f visualizer.log
	@$(RM) -f design.bin
	@$(RM) -f qwave.db
	@$(RM) -f transcript


# DSim
clean::
	@$(RM) -rf dsim.*
	@$(RM) -rf metrics.db
	@$(RM) -rf file.vcd

else
    $(warning Including Makefile.inc from a user makefile is a no-op and deprecated. Remove the Makefile.inc inclusion from your makefile, and only leave the Makefile.sim include.)
endif # COCOTB_MAKEFILE_INC_INCLUDED
