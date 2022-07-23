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

ifneq ($(SIM),)
all:
	@echo "Skipping issue_253 only runs on icarus"
else

include ../../designs/sample_module/Makefile

MODULE = issue_253

# Redefine the Icarus rule for results.xml to not specify TOPLEVEL, test should still pass

all: empty_top_level no_top_level notset_top_level

$(COCOTB_RESULTS_FILE):
	@echo "Skipping"

notset_top_level: $(SIM_BUILD)/sim.vvp $(CUSTOM_SIM_DEPS)
	MODULE=$(MODULE) \
	TESTCASE=issue_253_notset TOPLEVEL= \
	vvp -M $(shell cocotb-config --lib-dir) -m $(shell cocotb-config --lib-name vpi icarus) $(SIM_BUILD)/sim.vvp $(SIM_ARGS) $(EXTRA_ARGS) $(PLUSARGS)
	mkdir -p $@_result && mv results.xml $@_result/

empty_top_level: $(SIM_BUILD)/sim.vvp $(CUSTOM_SIM_DEPS)
	MODULE=$(MODULE) \
	TESTCASE=issue_253_empty TOPLEVEL="" \
	vvp -M $(shell cocotb-config --lib-dir) -m $(shell cocotb-config --lib-name vpi icarus) $(SIM_BUILD)/sim.vvp $(SIM_ARGS) $(EXTRA_ARGS) $(PLUSARGS)
	mkdir -p $@_result && mv results.xml $@_result/

no_top_level: $(SIM_BUILD)/sim.vvp $(CUSTOM_SIM_DEPS)
	MODULE=$(MODULE) \
	TESTCASE=issue_253_none \
	vvp -M $(shell cocotb-config --lib-dir) -m $(shell cocotb-config --lib-name vpi icarus) $(SIM_BUILD)/sim.vvp $(SIM_ARGS) $(EXTRA_ARGS) $(PLUSARGS)
	mkdir -p $@_result && mv results.xml $@_result/

endif

clean::
	$(RM) -r empty_top_level_result
	$(RM) -r no_top_level_result
	$(RM) -r notset_top_level_result
