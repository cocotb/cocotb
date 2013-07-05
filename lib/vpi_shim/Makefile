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
OBJ_DIR		:= obj
INCLUDES	+= 
GCC_ARGS	+=
LIBS		:= -lgpilog -lcocotb
LD_PATH		:= -L$(LIB_DIR)

SRCS		:= gpi_vpi.c
OBJS		:= $(SRCS:%.c=$(OBJ_DIR)/%.o)

LIB_NAME	:= libgpi.so

all: $(LIB_DIR)/gpivpi.vpl

$(OBJ_DIR)/%.o: %.c
	gcc $(GCC_ARGS) -c $(INCLUDES) -o $@ $<

$(OBJ_DIR):
	mkdir -p $(OBJ_DIR)

$(LIB_DIR)/$(LIB_NAME): $(OBJ_DIR) $(OBJS)
	gcc $(GCC_ARGS) $(LINKER_ARGS) -o $@ $(OBJS) $(LIBS) $(LD_PATH)

# More rules such that this may be needed depending on the requirements of
# different simulators, icarus for instance loads a <name>.vpi libraray to use the vpi
# inerface at the start of the simulation
$(LIB_DIR)/gpivpi.vpl: $(LIB_DIR)/$(LIB_NAME)
	ln -sf $(LIB_NAME) $@

clean:
	rm -rf $(OBJ_DIR)
