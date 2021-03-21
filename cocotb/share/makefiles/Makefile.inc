###############################################################################
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd,
#       SolarFlare Communications Inc nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
##############################################################################

# Common makefile included by everything

ifndef COCOTB_MAKEFILE_INC_INCLUDED # Protect against multiple includes
COCOTB_MAKEFILE_INC_INCLUDED = 1

# Default sim rule will force a re-run of the simulation (though the cocotb library
# and RTL compilation phases are still evaluated by makefile dependencies)
.PHONY: sim
sim:
	-@rm -f $(COCOTB_RESULTS_FILE)
	$(MAKE) $(COCOTB_RESULTS_FILE)

# Make sure to use bash for the pipefail option used in many simulator Makefiles
SHELL := bash

# Directory containing the cocotb Python module (realpath for Windows compatibility)
COCOTB_PY_DIR := $(realpath $(shell cocotb-config --prefix))

# Directory containing all support files required to build cocotb-based
# simulations: Makefile fragments, and the simulator libraries.
COCOTB_SHARE_DIR := $(COCOTB_PY_DIR)/cocotb/share

OS=$(shell uname)
ifneq (, $(findstring MINGW, $(OS)))
    OS := Msys
else ifneq (, $(findstring MSYS, $(OS)))
    OS := Msys
endif
export OS

# this ensures we use the same python as the one cocotb was installed into
# realpath to convert windows paths to unix paths, like cygpath -u
PYTHON_BIN ?= $(realpath $(shell cocotb-config --python-bin))

include $(COCOTB_SHARE_DIR)/makefiles/Makefile.deprecations

LIB_DIR=$(COCOTB_PY_DIR)/cocotb/libs

PYTHON_ARCH := $(shell $(PYTHON_BIN) -c 'from platform import architecture; print(architecture()[0])')
ifeq ($(filter $(PYTHON_ARCH),64bit 32bit),)
    $(error Unknown Python architecture: $(PYTHON_ARCH))
endif

# Set PYTHONHOME to properly populate sys.path in embedded python interpreter
export PYTHONHOME := $(shell $(PYTHON_BIN) -c 'from distutils.sysconfig import get_config_var; print(get_config_var("prefix"))')

ifeq ($(OS),Msys)
    to_tcl_path = $(shell cygpath -m $(1) )
else
    to_tcl_path = $(1)
endif

# Check that the COCOTB_RESULTS_FILE was created, since we can't set an exit code from cocotb.
define check_for_results_file
    @test -f $(COCOTB_RESULTS_FILE) || (echo "ERROR: $(COCOTB_RESULTS_FILE) was not written by the simulation!" >&2 && exit 1)
endef

SIM_BUILD ?= sim_build
export SIM_BUILD

COCOTB_RESULTS_FILE ?= results.xml
COCOTB_HDL_TIMEUNIT ?= 1ns
COCOTB_HDL_TIMEPRECISION ?= 1ps

export COCOTB_RESULTS_FILE

# Depend on all Python from the cocotb package. This triggers a
# recompilation of the simulation if cocotb is updated.
CUSTOM_SIM_DEPS += $(shell find $(COCOTB_PY_DIR)/cocotb/ -name "*.py")

# This triggers a recompilation of the simulation if cocotb library is updated.
CUSTOM_SIM_DEPS += $(shell find $(LIB_DIR)/ -name "*")

$(SIM_BUILD):
	mkdir -p $@

# Regression rule uses Make dependencies to determine whether to run the simulation
.PHONY: regression
regression: $(COCOTB_RESULTS_FILE)

# Attempt to detect TOPLEVEL_LANG based on available sources if not set
ifeq ($(TOPLEVEL_LANG),)

ifneq ($(and $(VHDL_SOURCES),$(if $(VERILOG_SOURCES),,1),)
	TOPLEVEL_LANG := vhdl
else ifneq ($(and $(VERILOG_SOURCES),$(if $(VHDL_SOURCES),,1),)
	TOPLEVEL_LANG := verilog
endif

endif

define find_libpython_errmsg =


find_libpython was not able to find a libpython in the current Python environment. Ensure
the Python development packages are installed. If they are installed and find_libpython
is not finding the path to libpython, file an upstream bug in find_libpython; then
manually override the LIBPYTHON_LOC make variable with the absolute path to libpython.so
(or python.dll on Windows).

endef

# get the path to libpython and the return code from the script
# adapted from https://stackoverflow.com/a/24658961/6614127
FIND_LIBPYTHON_RES := $(shell cocotb-config --libpython; echo $$?)
FIND_LIBPYTHON_RC := $(lastword $(FIND_LIBPYTHON_RES))
LIBPYTHON_LOC := $(strip $(subst $(FIND_LIBPYTHON_RC)QQQQ,,$(FIND_LIBPYTHON_RES)QQQQ))

# complain if libpython isn't found, and export otherwise
ifneq ($(FIND_LIBPYTHON_RC),0)
    $(error $(find_libpython_errmsg))
endif
export LIBPYTHON_LOC

else
    $(warning Including Makefile.inc from a user makefile is a no-op and deprecated. Remove the Makefile.inc inclusion from your makefile, and only leave the Makefile.sim include.)
endif # COCOTB_MAKEFILE_INC_INCLUDED
