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
###############################################################################

include $(COCOTB_SHARE_DIR)/makefiles/Makefile.inc

INCLUDES    +=
GXX_ARGS    += -DVPI_CHECKING
LIBS        := $(EXTRA_LIBS) -lgpilog -lgpi -lstdc++
LD_PATH     := $(EXTRA_LIBDIRS) -L$(LIB_DIR)
LIB_NAME    := libvpi

SRCS        := VpiImpl.cpp VpiCbHdl.cpp

CLIBS       += $(LIB_DIR)/gpivpi.vpl

#temporary hack for cvc
ifeq ($(SIM),cvc)
    GXX_ARGS    += -DMODELSIM
endif

# More rules such that this may be needed depending on the requirements of
# different simulators, icarus for instance loads a <name>.vpi libraray to use the vpi
# inerface at the start of the simulation

all: $(LIB_DIR)/gpivpi.vpl $(LIB_DIR)/cocotb.vpi

$(LIB_DIR)/gpivpi.vpl: $(LIB_DIR)/$(LIB_NAME).$(LIB_EXT)
	ln -sf $(LIB_NAME).$(LIB_EXT) $@

$(LIB_DIR)/cocotb.vpi: $(LIB_DIR)/$(LIB_NAME).$(LIB_EXT)
	ln -sf $(LIB_NAME).$(LIB_EXT) $@

clean:
	-@rm -rf $(LIB_DIR)/$(LIB_NAME).$(LIB_EXT)
	-@rm -rf $(LIB_DIR)/gpivpi.vpl
	-@rm -rf $(LIB_DIR)/cocotb.vpi

include $(COCOTB_SHARE_DIR)/makefiles/Makefile.rules
