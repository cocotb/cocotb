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

ifeq ($(USER_DIR),)
export USER_DIR:=$(realpath $(dir $(firstword $(MAKEFILE_LIST))))
endif

BUILD_DIR=$(USER_DIR)/build
export BUILD_DIR

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
PYTHON_BIN ?= $(shell cocotb-config --python-bin)

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

export LIB_DIR=$(COCOTB_PY_DIR)/cocotb/libs

ifeq ($(OS),Msys)
LIB_EXT    := dll
else
LIB_EXT    := so
endif
