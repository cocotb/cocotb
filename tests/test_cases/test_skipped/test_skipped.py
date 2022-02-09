# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import pathlib

import cocotb

skipped_file_name = "ran_skipped_test~"


@cocotb.test(skip=True)
async def test_skipped(dut):
    """Touch a file so we can check that this test has run."""
    pathlib.Path(skipped_file_name).touch()
