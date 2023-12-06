# Copyright cocotb contributors
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
endif
endif

ifeq ($(SKIP),)

include ../../designs/defaultless_parameter_module/Makefile

MODULE = test_defaultless_parameter

else

all:
	@echo "Skipping test_defaultless_parameter since icarus < v12.0 doesn't support defaultless parameters"

clean::
# nothing to clean, just define target in this branch

endif
