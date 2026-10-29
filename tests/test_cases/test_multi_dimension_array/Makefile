# Copyright cocotb contributors
# Copyright (c) 2016, 2018 Potential Ventures Ltd
# Copyright (c) 2016 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause


ifeq ($(SIM),)
USING_ICARUS := 1
endif

ifeq ($(shell echo $(SIM) | tr A-Z a-z),icarus)
USING_ICARUS := 1
endif

ifneq ($(USING_ICARUS),)
ICARUS_MIN := 12.0
ICARUS_VERSION := $(shell iverilog -V 2>/dev/null | head -n1 | cut -d ' ' -f 4)
MIN_VERSION := $(shell printf "%s\n%s\n" "$(ICARUS_MIN)" "$(ICARUS_VERSION)" | sort -g | head -1)
ifneq ($(MIN_VERSION),$(ICARUS_MIN))
SKIP := 1
$(info Skipping test_multi_dimension_array since icarus < v$(ICARUS_MIN) doesn't support the design syntax)
endif
endif

ifeq ($(SKIP),)

include ../../designs/multi_dimension_array/Makefile

COCOTB_TEST_MODULES = test_cocotb_array

else

all:

clean::

endif
