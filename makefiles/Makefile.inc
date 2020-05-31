# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

$(error Outdated use of cocotb detected. \
        Please install cocotb, and modify your makefile to \
        "include $$(shell cocotb-config --makefile)/Makefile.sim" instead. \
        Please refer to the documentation at https://docs.cocotb.org.)
