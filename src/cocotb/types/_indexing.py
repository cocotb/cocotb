# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os

from cocotb.types._range import Range

do_indexing_changed_warning = os.environ.get("COCOTB_INDEXING_CHANGED_WARNING")


def indexing_changed(range: Range) -> bool:
    return not (range.left == 0 and range.direction == "to")


class IndexingChangedWarning(UserWarning):
    """Warning issued when a value is indexed in a way that is different between cocotb 1.x and 2.x."""
