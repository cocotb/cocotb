# Copyright cocotb contributors
# Copyright (c) 2013, 2018 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

EXAMPLES := adder/tests \
            simple_dff \
            matrix_multiplier/tests \
            mixed_language/tests \

ifeq ($(TOPLEVEL_LANG),verilog)
    ifeq ($(SIM),$(filter $(SIM),ius xcelium))
        ifeq (,$(shell which spectre))
            $(info Skipping example mixed_signal since Spectre is not available)
        else
            EXAMPLES += mixed_signal/tests
        endif
    else
        $(info Skipping example mixed_signal since only Xcelium is supported)
    endif
    EXAMPLES += doc_examples/quickstart
endif

.PHONY: $(EXAMPLES)

.PHONY: all
all: $(EXAMPLES)

$(EXAMPLES):
	@cd $@ && $(MAKE)

.PHONY: clean
clean:
	$(foreach TEST, $(EXAMPLES), $(MAKE) -C $(TEST) clean;)

regression:
	$(foreach TEST, $(EXAMPLES), $(MAKE) -C $(TEST) regression;)
