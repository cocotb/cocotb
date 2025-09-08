# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

COCOTB_TEST_MODULES := kill_sim_tests

SKIP := 0
ifeq ($(SIM),riviera)
  # Determine the version of Riviera-PRO being used.
  # Assume "python3" to be available, the exact version does not matter much
  # in this context.
  RIVIERA_VERSION_INT := $(shell vsimsa -version | python3 -c 'import re,sys; m=re.match(r".+version (\d+)\.(\d+).+", sys.stdin.read()); print(f"{int(m[1])*100+int(m[2])}")')

  ifeq ($(shell test $(RIVIERA_VERSION_INT) -lt 202404; echo $$?),0)
    $(info Skipping test for Riviera-PRO versions < 2024.04 due to a shutdown hang)
    SKIP := 1
  endif
endif

.PHONY: tests
tests:
	$(MAKE) test_kill_sim COCOTB_TEST_FILTER=test_sys_exit
	$(MAKE) test_kill_sim COCOTB_TEST_FILTER=test_task_sys_exit
ifneq ($(SKIP),1)
	$(MAKE) test_kill_sim COCOTB_TEST_FILTER=test_trigger_sys_exit
endif
	$(MAKE) test_kill_sim COCOTB_TEST_FILTER=test_keyboard_interrupt
	$(MAKE) test_kill_sim COCOTB_TEST_FILTER=test_task_keyboard_interrupt
ifneq ($(SKIP),1)
	$(MAKE) test_kill_sim COCOTB_TEST_FILTER=test_trigger_keyboard_interrupt
endif

.PHONY: test_kill_sim
test_kill_sim:
	$(RM) -f test_failed
	-$(MAKE) sim
	test ! -f test_failed

include ../../designs/sample_module/Makefile
