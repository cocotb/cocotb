# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

run:
	$(RM) number
	$(MAKE) sim COCOTB_TEST_MODULES=test_other,test_seed COCOTB_RANDOM_SEED=1234
	$(MAKE) sim COCOTB_TEST_MODULES=test_seed COCOTB_TEST_FILTER=test_reproducibility COCOTB_RANDOM_SEED=1234

include ../../designs/sample_module/Makefile
