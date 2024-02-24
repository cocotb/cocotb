###############################################################################
# Copyright (c) 2016, 2018 Potential Ventures Ltd
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


ifeq ($(SIM),)
USING_ICARUS := 1
endif

ifeq ($(shell echo $(SIM) | tr A-Z a-z),icarus)
USING_ICARUS := 1
endif

ifneq ($(USING_ICARUS),)
ICARUS_MIN := 11.0
ICARUS_VERSION := $(shell iverilog -V 2>/dev/null | head -n1 | cut -d ' ' -f 4)
MIN_VERSION := $(shell printf "%s\n%s\n" "$(ICARUS_MIN)" "$(ICARUS_VERSION)" | sort -g | head -1)
ifneq ($(MIN_VERSION),$(ICARUS_MIN))
SKIP := 1
$(info Skipping test_multi_dimension_array since icarus < v$(ICARUS_MIN) doesn't support packages)
endif
endif

ifeq ($(SKIP),)

include ../../designs/multi_dimension_array/Makefile

MODULE = test_cocotb_array

else

all:

clean::

endif
