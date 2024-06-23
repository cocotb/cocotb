# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

TOPLEVEL_LANG ?= verilog
TOPLEVEL := fatal
MODULE := test_fatal

PWD=$(shell pwd)

ifeq ($(TOPLEVEL_LANG),verilog)
    VERILOG_SOURCES := $(PWD)/fatal.sv
else ifeq ($(TOPLEVEL_LANG),vhdl)
    VHDL_SOURCES := $(PWD)/fatal.vhd
    ifneq ($(filter $(SIM),ius xcelium),)
        COMPILE_ARGS += -v93
    endif
endif

ifeq ($(shell echo $(SIM) | tr A-Z a-z),verilator)
    COMPILE_ARGS += --timing

# error if results file exists, because currently verilator cannot find root handle with an empty module containing $fatal (gh-2346)
.PHONY: verilator_override_for_this_test
verilator_override_for_this_test:
	-$(MAKE) all
	@test ! -f $(COCOTB_RESULTS_FILE) || (echo "ERROR: $(COCOTB_RESULTS_FILE) was written by Verilator but not expected to" >&2 && exit 1)
else
# squash error code from simulator and ensure the cocotb test passed
.PHONY: override_for_this_test
override_for_this_test:
	-$(MAKE) all
	$(call check_for_results_file)
	python -m cocotb_tools.combine_results &> /dev/null
endif

include $(shell cocotb-config --makefiles)/Makefile.sim
