# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations


def entry_func() -> None:
    with open("results.log", "w") as file:
        print("got entry", file=file)
