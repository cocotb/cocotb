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


# FIXME it's a bit nasty to have the source files listed here as dependencies
# but better than re-building the libraries every time.

$(LIB_OBJ_DIR):
	mkdir -p $@

$(LIB_DIR): $(LIB_OBJ_DIR)
	mkdir -p $@

$(LIB_DIR)/libgpilog.$(LIB_EXT): $(COCOTB_SHARE_DIR)/lib/gpi_log/gpi_logging.c | $(LIB_DIR)
	make -C $(COCOTB_SHARE_DIR)/lib/gpi_log SIM=$(SIM)

$(LIB_DIR)/libcocotb.$(LIB_EXT): $(COCOTB_SHARE_DIR)/lib/embed/gpi_embed.c | $(LIB_DIR)
	make -C $(COCOTB_SHARE_DIR)/lib/embed SIM=$(SIM)

$(LIB_DIR)/libvpi.$(LIB_EXT): $(COCOTB_SHARE_DIR)/lib/vpi/VpiImpl.cpp $(COCOTB_SHARE_DIR)/lib/vpi/VpiCbHdl.cpp | $(LIB_DIR)
	make -C $(COCOTB_SHARE_DIR)/lib/vpi EXTRA_LIBS=$(EXTRA_LIBS) EXTRA_LIBDIRS=$(EXTRA_LIBDIRS) SIM=$(SIM)

$(LIB_DIR)/libcocotbvhpi.$(LIB_EXT): $(COCOTB_SHARE_DIR)/lib/vhpi/VhpiImpl.cpp $(COCOTB_SHARE_DIR)/lib/vhpi/VhpiCbHdl.cpp | $(LIB_DIR)
	make -C $(COCOTB_SHARE_DIR)/lib/vhpi EXTRA_LIBS=$(EXTRA_LIBS) EXTRA_LIBDIRS=$(EXTRA_LIBDIRS) SIM=$(SIM)

$(LIB_DIR)/libgpi.$(LIB_EXT): $(COCOTB_SHARE_DIR)/lib/gpi/GpiCommon.cpp $(COCOTB_SHARE_DIR)/lib/gpi/GpiCbHdl.cpp | $(LIB_DIR)
	make -C $(COCOTB_SHARE_DIR)/lib/gpi EXTRA_LIBS=$(EXTRA_LIBS) EXTRA_LIBDIRS=$(EXTRA_LIBDIRS) SIM=$(SIM)

$(LIB_DIR)/libfli.$(LIB_EXT): $(COCOTB_SHARE_DIR)/lib/fli/FliImpl.cpp $(COCOTB_SHARE_DIR)/lib/fli/FliCbHdl.cpp $(COCOTB_SHARE_DIR)/lib/fli/FliObjHdl.cpp | $(LIB_DIR)
	make -C $(COCOTB_SHARE_DIR)/lib/fli EXTRA_LIBS=$(EXTRA_LIBS) EXTRA_LIBDIRS=$(EXTRA_LIBDIRS) SIM=$(SIM)

$(LIB_DIR)/libsim.$(LIB_EXT): $(COCOTB_SHARE_DIR)/lib/simulator/simulatormodule.c | $(LIB_DIR)
	make -C $(COCOTB_SHARE_DIR)/lib/simulator SIM=$(SIM)

$(LIB_DIR)/libcocotbutils.$(LIB_EXT): $(COCOTB_SHARE_DIR)/lib/utils/cocotb_utils.c | $(LIB_DIR)
	make -C $(COCOTB_SHARE_DIR)/lib/utils SIM=$(SIM)

COCOTB_LIBS := $(LIB_DIR)/libcocotbutils.$(LIB_EXT) \
	       $(LIB_DIR)/libgpilog.$(LIB_EXT) \
	       $(LIB_DIR)/libcocotb.$(LIB_EXT) \
	       $(LIB_DIR)/libgpi.$(LIB_EXT) \
	       $(LIB_DIR)/libsim.$(LIB_EXT) \

COCOTB_VPI_LIB := $(LIB_DIR)/libvpi.$(LIB_EXT)

COCOTB_VHPI_LIB := $(LIB_DIR)/libcocotbvhpi.$(LIB_EXT)

COCOTB_FLI_LIB := $(LIB_DIR)/libfli.$(LIB_EXT)

clean::
	-@rm -rf $(BUILD_DIR)
