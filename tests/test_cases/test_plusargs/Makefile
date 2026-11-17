# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

ifeq ($(shell echo $(SIM) | tr A-Z a-z)-$(TOPLEVEL_LANG),vcs-vhdl)
all:
	@echo "Skipping test_plusargs since VCS does not accept plusargs for designs with VHDL sources only"
clean::

else

include ../../designs/plusargs_module/Makefile

COCOTB_PLUSARGS=+foo=bar +test1 +test2 +options=fubar +lol=wow=4

COCOTB_TEST_MODULES = plusargs
endif
