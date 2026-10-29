# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

.PHONY: override_tests
override_tests:
	$(MAKE) COCOTB_TRUST_INERTIAL_WRITES=0 sim COCOTB_RESULTS_FILE=results_no_trust.xml
	$(MAKE) COCOTB_TRUST_INERTIAL_WRITES=1 sim COCOTB_RESULTS_FILE=results_trust.xml

COCOTB_TEST_MODULES := inertial_writes_tests

include ../../designs/sample_module/Makefile

simulator_test:
	$(MAKE) COCOTB_TRUST_INERTIAL_WRITES=1 COCOTB_SIMULATOR_TEST=1 sim
