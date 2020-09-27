###############################################################################
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
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

.PHONY: all
all: test

.PHONY: clean
clean:
	-@find . -name "obj" | xargs rm -rf
	-@find . -name "*.pyc" | xargs rm -rf
	-@find . -name "*results.xml" | xargs rm -rf
	$(MAKE) -C examples clean
	$(MAKE) -C tests clean

.PHONY: do_tests
do_tests::
	$(MAKE) -k -C tests
do_tests::
	$(MAKE) -k -C examples
# increase coverage
do_tests::
	$(MAKE) -k -C tests/test_cases/test_cocotb/ COCOTB_LOG_LEVEL=DEBUG > test_cocotb_DEBUG.log
do_tests::
	$(MAKE) -k -C tests/test_cases/test_cocotb/ COCOTB_SCHEDULER_DEBUG=1 > test_cocotb_SCHEDULER_DEBUG.log

# For Jenkins we use the exit code to detect compile errors or catastrophic
# failures and the XML to track test results
.PHONY: jenkins
jenkins: do_tests
	./bin/combine_results.py --suppress_rc --testsuites_name=cocotb_regression

# By default want the exit code to indicate the test results
.PHONY: test
test:
	$(MAKE) do_tests; ret=$$?; ./bin/combine_results.py && exit $$ret

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
