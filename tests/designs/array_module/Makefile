###############################################################################
# Copyright (c) 2016 Potential Ventures Ltd
# Copyright (c) 2016 SolarFlare Communications Inc
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

TOPLEVEL_LANG ?= verilog

COCOTB_TOPLEVEL := array_module

PWD=$(shell pwd)

COCOTB?=$(PWD)/../../..

ifeq ($(TOPLEVEL_LANG),verilog)
    VERILOG_SOURCES = $(COCOTB)/tests/designs/array_module/array_module.sv
else ifeq ($(TOPLEVEL_LANG),vhdl)
    ifneq ($(filter $(SIM),ius xcelium),)
        COMPILE_ARGS += -v93
    endif
ifeq ($(shell echo $(SIM) | tr A-Z a-z),aldec)
    VHDL_SOURCES =  $(COCOTB)/tests/designs/array_module/array_module_pack.vhd $(COCOTB)/tests/designs/array_module/array_module_aldec.vhd
else
    VHDL_SOURCES =  $(COCOTB)/tests/designs/array_module/array_module_pack.vhd $(COCOTB)/tests/designs/array_module/array_module.vhd
endif
else
    $(error A valid value (verilog or vhdl) was not provided for TOPLEVEL_LANG=$(TOPLEVEL_LANG))
endif

include $(shell cocotb-config --makefiles)/Makefile.sim
