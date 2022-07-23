# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

run:
	$(RM) number
	$(MAKE) sim MODULE=test_other,test_seed RANDOM_SEED=1234
	$(MAKE) sim MODULE=test_seed TESTCASE=test_reproducibility RANDOM_SEED=1234

include ../../designs/sample_module/Makefile
