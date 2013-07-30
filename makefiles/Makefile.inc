###############################################################################
# Copyright (c) 2013 Potential Ventures Ltd
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd nor the
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

ifeq ($(SIM_ROOT),)
export SIM_ROOT:=$(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
endif

ifeq ($(USER_DIR),)
export USER_DIR:=$(SIM_ROOT)
endif

BUILD_DIR=$(USER_DIR)/build
export BUILD_DIR

ARCH?=$(shell uname -m)
export ARCH

OS=$(shell uname)
export OS

include $(SIM_ROOT)/makefiles/Makefile.paths
include $(SIM_ROOT)/makefiles/Makefile.pylib

export LIB_DIR=$(BUILD_DIR)/libs/$(ARCH)
export LIB_OBJ_DIR:= $(BUILD_DIR)/libs/$(ARCH)/obj
export INCLUDES := -I$(SIM_ROOT)/include $(PYTHON_INCLUDEDIR)



# Base GCC flags
ifeq ($(OS),Darwin)
GCC_ARGS    :=  -g -DDEBUG -fpic
else
GCC_ARGS	:=	-Werror -Wcast-qual -Wcast-align -Wwrite-strings \
				-Waggregate-return -Wstrict-prototypes           \
				-Wno-unused-parameter -fno-common -g -DDEBUG -fpic
ifeq ($(ARCH),i686)
GCC_ARGS    += -m32
endif
endif


ifeq ($(OS),Darwin)
LINKER_ARGS := -shared -undefined suppress -flat_namespace -L$(PYTHON_LIBDIR)
else
LINKER_ARGS := -shared -Xlinker -export-dynamic
endif
