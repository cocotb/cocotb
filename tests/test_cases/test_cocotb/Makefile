# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

include ../../designs/sample_module/Makefile

MODULE := "\
	test_deprecated,\
	test_synchronization_primitives,\
	test_concurrency_primitives,\
	test_tests,\
	test_testfactory,\
	test_generator_coroutines,\
	test_timing_triggers,\
	test_scheduler,\
	test_clock,\
	test_edge_triggers,\
	test_async_coroutines,\
	test_handle,\
	test_logging,\
	test_pytest,\
	test_queues,\
	"

ifeq ($(shell python -c "import sys; print(sys.version_info >= (3, 6))"), "True")
MODULE += test_async_generators,
endif
