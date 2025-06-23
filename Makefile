# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

REPO_ROOT := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

.PHONY: all
all: test

.PHONY: clean
clean:
	-@find . -name "obj" -exec rm -rf {} +
	-@find . -name "*.pyc" -delete
	-@find . -name "*results.xml" -delete
	$(MAKE) -C examples clean
	$(MAKE) -C tests clean

.PHONY: do_tests
do_tests::
	$(MAKE) -C tests
do_tests::
	$(MAKE) -C examples

# For Jenkins we use the exit code to detect compile errors or catastrophic
# failures and the XML to track test results
.PHONY: jenkins
jenkins: do_tests
	python -m cocotb_tools.combine_results --repo-root $(REPO_ROOT) --suppress_rc --testsuites_name=cocotb_regression

# By default want the exit code to indicate the test results
.PHONY: test
test:
	$(MAKE) do_tests; ret=$$?; python -m cocotb_tools.combine_results --repo-root $(REPO_ROOT) && exit $$ret

COCOTB_MAKEFILES_DIR = $(realpath $(shell cocotb-config --makefiles))
AVAILABLE_SIMULATORS = $(patsubst .%,%,$(suffix $(wildcard $(COCOTB_MAKEFILES_DIR)/simulators/Makefile.*)))

.PHONY: help
help:
	@echo ""
	@echo "This cocotb makefile has the following targets"
	@echo ""
	@echo "all, test - run regression producing combined_results.xml"
	@echo "            (return error code produced by sub-makes)"
	@echo "jenkins   - run regression producing combined_results.xml"
	@echo "            (return error code 1 if any failure was found)"
	@echo "clean     - remove build directory and all simulation artefacts"
	@echo ""
	@echo "The default simulator is Icarus Verilog."
	@echo "To use another, set the environment variable SIM as below."
	@echo "Available simulators:"
	@for X in $(sort $(AVAILABLE_SIMULATORS)); do \
		echo export SIM=$$X; \
	done
	@echo ""
