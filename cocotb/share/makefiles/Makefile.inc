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

# Directory containing the cocotb Python module (realpath for Windows compatibility)
COCOTB_PY_DIR := $(realpath $(shell cocotb-config --prefix))

# Directory containing all support files required to build cocotb-based
# simulations: Makefile fragments, and the simulator libraries.
COCOTB_SHARE_DIR := $(COCOTB_PY_DIR)/cocotb/share

ARCH?=$(shell uname -m)
export ARCH

OS=$(shell uname)
ifneq (, $(findstring MINGW, $(OS)))
OS=Msys
else ifneq (, $(findstring MSYS, $(OS)))
OS=Msys
endif
export OS

# this ensures we use the same python as the one cocotb was installed into
# realpath to convert windows paths to unix paths, like cygpath -u
PYTHON_BIN ?= $(realpath $(shell cocotb-config --python-bin))

include $(COCOTB_SHARE_DIR)/makefiles/Makefile.deprecations
include $(COCOTB_SHARE_DIR)/makefiles/Makefile.pylib

# Default to Icarus if no simulator is defined
SIM ?= icarus

SIM_DEFINE := $(shell echo $(SIM) | tr a-z A-Z)

# Use a common define for Questa and Modelsim and cvc
ifeq ($(SIM_DEFINE),$(filter $(SIM_DEFINE),QUESTA CVC))
SIM_DEFINE = MODELSIM
endif

# Use a common define for Xcelium and IUS
ifeq ($(SIM_DEFINE),XCELIUM)
SIM_DEFINE = IUS
endif

LIB_DIR=$(COCOTB_PY_DIR)/cocotb/libs

ifeq ($(OS),Msys)
LIB_EXT    := dll
else
LIB_EXT    := so
endif

# Set PYTHONHOME to properly populate sys.path in embedded python interpreter
export PYTHONHOME := $(shell $(PYTHON_BIN) -c 'from distutils.sysconfig import get_config_var; print(get_config_var("prefix"))')

ifeq ($(OS),Msys)
    # On Windows there is no support for @rpath/LD_LIBRARY_PATH so we need to set PATH to find cocotb libraries
    # https://docs.microsoft.com/en-us/windows/win32/dlls/dynamic-link-library-search-order?redirectedfrom=MSDN#standard-search-order-for-desktop-applications
    export PATH := $(LIB_DIR):$(PATH)
endif

ifeq ($(OS),Msys)
    to_tcl_path = $(shell cygpath -m $(1) )
else
    to_tcl_path = $(1)
endif
