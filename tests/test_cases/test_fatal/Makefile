# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

TOPLEVEL_LANG ?= verilog
TOPLEVEL := fatal
MODULE := test_fatal

ifeq ($(TOPLEVEL_LANG),verilog)
	VERILOG_SOURCES := fatal.sv
else ifeq ($(TOPLEVEL_LANG),vhdl)
	VHDL_SOURCES := fatal.vhd
endif

# squash error code from simulator and ensure the cocotb test passed
.PHONY: override_for_this_test
override_for_this_test:
	-$(MAKE) all
	$(call check_for_results_file)
	../../../bin/combine_results.py &> /dev/null

include $(shell cocotb-config --makefiles)/Makefile.sim
