# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
This file exists because Mac's grep (BSD) does not support either the -P or -z flags,
which are required to check the test listing result because it must match multiple lines.
"""

from __future__ import annotations

import re
import sys

with open(sys.argv[1]) as f:
    log = f.read()
    found = re.search(
        r"test_listing_1\.test_a\n.*test_listing_1\.test_b\n.*test_listing_2\.test_a\n.*test_listing_2\.test_b",
        log,
        re.MULTILINE,
    )
    if not found:
        print("Did not find expected test listing in sim.log")
        sys.exit(1)
