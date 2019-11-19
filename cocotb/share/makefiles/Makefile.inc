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

# Directory containing the cocotb Python module
ifeq ($(COCOTB_PY_DIR),)
export COCOTB_PY_DIR:=$(realpath $(dir $(lastword $(MAKEFILE_LIST)))/../../..)
endif

# Directory containing all support files required to build cocotb-based
# simulations: Makefile fragments, and the simulator libraries.
ifeq ($(COCOTB_SHARE_DIR),)
export COCOTB_SHARE_DIR:=$(realpath $(dir $(lastword $(MAKEFILE_LIST)))/..)
endif

ifeq ($(COCOTB_PY_DIR),$(COCOTB_SHARE_DIR))
$(warning 'Deprecated cocotb file structure detected. Please use "include $$(shell cocotb-config --makefile)/Makefile.inc" in Makefiles')
endif

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

include $(COCOTB_SHARE_DIR)/makefiles/Makefile.paths
include $(COCOTB_SHARE_DIR)/makefiles/Makefile.pylib

export LIB_DIR=$(BUILD_DIR)/libs/$(ARCH)
export LIB_OBJ_DIR:= $(BUILD_DIR)/obj/$(ARCH)
export INCLUDES := -I$(COCOTB_SHARE_DIR)/include -I$(PYTHON_INCLUDEDIR)

LIB_EXT     := so
PY_EXT	    := so

# Base GCC flags
ifeq ($(ARCH),i686)
GXX_ARGS    := -m32
endif

ifeq ($(OS),Darwin)
GXX_ARGS	+= -g -DDEBUG -fpic
GCC_ARGS	:= $(GXX_ARGS)
else ifeq ($(OS),Msys)
GXX_ARGS 	+= -g -DDEBUG -shared
ifeq ($(ARCH),x86_64)
GXX_ARGS  += -DMS_WIN64
endif
GCC_ARGS	:= $(GXX_ARGS)
LIB_EXT		:= dll
PY_EXT		:= pyd
else ifeq ($(OS),Linux)
GXX_ARGS	+= -Werror -Wcast-qual -Wcast-align -Wwrite-strings \
			-Wall -Wno-unused-parameter \
			-fno-common -g -DDEBUG -fpic
GCC_ARGS	:= $(GXX_ARGS) -Wstrict-prototypes -Waggregate-return
else
$(error "Unsupported os " $(OS))
endif

ifeq ($(OS),Darwin)
SO_LINKER_ARGS := -shared -undefined suppress -flat_namespace -L$(PYTHON_LIBDIR)
else ifeq ($(OS),Linux)
SO_LINKER_ARGS := -shared -Xlinker -L$(PYTHON_LIBDIR)
else ifeq ($(OS),Msys)
SO_LINKER_ARGS :=  -shared -Wl,-no-undefined -Wl,-enable-runtime-pseudo-reloc-v2 \
			-Wl,--enable-auto-import -L$(PYTHON_LIBDIR)
else
$(error "Unsupported os" $(OS))
endif
