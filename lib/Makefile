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
###############################################################################

include $(SIM_ROOT)/makefiles/Makefile.inc

CLIBS:= $(SIM_ROOT)/lib/gpi \
		$(SIM_ROOT)/lib/embed \
		$(SIM_ROOT)/lib/vpi_shim \
		$(SIM_ROOT)/lib/simulator

libs_native: $(CLIBS)

force_32:
	ARCH=i686 make

$(SIM_ROOT)/lib/vpi_shim: $(SIM_ROOT)/lib/gpi $(SIM_ROOT)/lib/embed
$(SIM_ROOT)/lib/simulator: $(SIM_ROOT)/lib/vpi_shim

$(LIB_OBJ_DIR):
	mkdir -p $@

$(LIB_DIR): $(LIB_OBJ_DIR)
	mkdir -p $@

$(CLIBS): $(LIB_DIR)
	$(MAKE) -C $@

clean_lib:
	-@rm -rf $(BUILD_DIR)
