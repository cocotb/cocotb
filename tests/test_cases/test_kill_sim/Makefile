# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

COCOTB_TEST_MODULES := kill_sim_tests

.PHONY: tests
tests:
	$(MAKE) test_kill_sim COCOTB_TEST_FILTER=test_sys_exit
	$(MAKE) test_kill_sim COCOTB_TEST_FILTER=test_task_sys_exit
	$(MAKE) test_kill_sim COCOTB_TEST_FILTER=test_keyboard_interrupt
	$(MAKE) test_kill_sim COCOTB_TEST_FILTER=test_task_keyboard_interrupt

.PHONY: test_kill_sim
test_kill_sim:
	$(RM) -f test_failed
	-$(MAKE) sim
	test ! -f test_failed

include ../../designs/sample_module/Makefile
