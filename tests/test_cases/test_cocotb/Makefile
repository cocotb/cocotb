# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

include ../../designs/sample_module/Makefile

# The pytest_assertion_rewriting test module deliberately does not follow the
# test_* naming convention to test that pytest assertion rewriting is enabled
# on all test modules declared in COCOTB_TEST_MODULES (gh-3011)
COCOTB_TEST_MODULES := "\
	test_deprecated,\
	test_synchronization_primitives,\
	test_first_combine,\
	test_tests,\
	test_testfactory,\
	test_timing_triggers,\
	test_scheduler,\
	test_clock,\
	test_edge_triggers,\
	test_async_coroutines,\
	test_async_generators,\
	test_handle,\
	test_logging,\
	pytest_assertion_rewriting,\
	test_queues,\
	test_sim_time_utils,\
	test_start_soon,\
	test_ci,\
	test_waiters,\
	test_task_manager,\
	"

# test_timing_triggers.py requires a 1ps time precision.
COCOTB_HDL_TIMEPRECISION := 1ps
