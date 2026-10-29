# Copyright cocotb contributors
# Copyright (c) 2015 Potential Ventures Ltd
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

include ../../designs/viterbi_decoder_axi4s/Makefile
COCOTB_TEST_MODULES = test_iteration

ifneq ($(filter $(SIM),ius xcelium),)
    SIM_ARGS += -notimezeroasrtmsg
endif

ifeq ($(SIM),ghdl)
    SIM_ARGS += --ieee-asserts=disable-at-0
endif
