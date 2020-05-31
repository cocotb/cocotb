# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

include $(shell cocotb-config --makefiles)/Makefile.inc

ifneq ($(VHDL_SOURCES),)

results.xml:
	@echo "Skipping simulation as VHDL is not supported on simulator=$(SIM)"
debug: results.xml
clean::

else

CMD := verilator

ifeq ($(shell which $(CMD) 2>/dev/null),)
# Verilator is not in PATH, lets start searching for it
$(error Cannot find verilator.)
endif

ifeq ($(VERILATOR_SIM_DEBUG), 1)
  COMPILE_ARGS += --debug
  PLUSARGS += +verilator+debug
  SIM_BUILD_FLAGS += -DVL_DEBUG
endif

ifeq ($(VERILATOR_TRACE),1)
  EXTRA_ARGS += --trace --trace-structs
endif

ifdef COCOTB_HDL_TIMEPRECISION
  SIM_BUILD_FLAGS += -DVL_TIME_PRECISION_STR=$(COCOTB_HDL_TIMEPRECISION)
endif

SIM_BUILD_FLAGS += -std=c++11

COMPILE_ARGS += --vpi --public-flat-rw --prefix Vtop -o $(TOPLEVEL) -LDFLAGS "-Wl,-rpath,$(LIB_DIR) -L$(LIB_DIR) -lcocotbvpi_verilator -lgpi -lcocotb -lgpilog -lcocotbutils"

$(SIM_BUILD)/Vtop.mk: $(VERILOG_SOURCES) $(CUSTOM_COMPILE_DEPS) $(COCOTB_SHARE_DIR)/lib/verilator/verilator.cpp | $(SIM_BUILD)
	$(CMD) -cc --exe -Mdir $(SIM_BUILD) -DCOCOTB_SIM=1 --top-module $(TOPLEVEL) $(COMPILE_ARGS) $(EXTRA_ARGS) $(VERILOG_SOURCES) $(COCOTB_SHARE_DIR)/lib/verilator/verilator.cpp

# Compilation phase
$(SIM_BUILD)/$(TOPLEVEL): $(SIM_BUILD)/Vtop.mk
	CPPFLAGS="$(SIM_BUILD_FLAGS)" make -C $(SIM_BUILD) -f Vtop.mk

$(COCOTB_RESULTS_FILE): $(SIM_BUILD)/$(TOPLEVEL) $(CUSTOM_SIM_DEPS)
	-@rm -f $(COCOTB_RESULTS_FILE)

	MODULE=$(MODULE) TESTCASE=$(TESTCASE) TOPLEVEL=$(TOPLEVEL) TOPLEVEL_LANG=$(TOPLEVEL_LANG) \
        $< $(PLUSARGS)

	$(call check_for_results_file)

debug: $(SIM_BUILD)/$(TOPLEVEL) $(CUSTOM_SIM_DEPS)
	-@rm -f $(COCOTB_RESULTS_FILE)

	MODULE=$(MODULE) TESTCASE=$(TESTCASE) TOPLEVEL=$(TOPLEVEL) TOPLEVEL_LANG=$(TOPLEVEL_LANG) \
        gdb --args $< $(PLUSARGS)

	$(call check_for_results_file)

clean::
	@rm -rf $(SIM_BUILD)
	@rm -f dump.vcd

endif
