# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import random

import cocotb


@cocotb.test()
async def test_first(_):
    # move generator to test that it doesn't affect the next test
    for _ in range(100):
        random.getrandbits(64)


@cocotb.test()
async def test_reproducibility(_):
    try:
        with open("number") as file:
            a = int(file.read())
        assert a == random.getrandbits(32)
    except FileNotFoundError:
        with open("number", "w") as file:
            number = random.getrandbits(32)
            file.write(str(number))
