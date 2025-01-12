# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import os
import sys
from typing import Any


def start_cocotb_library_coverage(_: Any) -> None:  # pragma: no cover
    if "COCOTB_LIBRARY_COVERAGE" not in os.environ:
        return
    try:
        import coverage
    except (ImportError, ModuleNotFoundError):
        print(
            "cocotb library coverage collection requested but coverage package not available. Install it using `pip install coverage`.",
            file=sys.stderr,
        )
    else:
        library_coverage = coverage.coverage(
            data_file=".coverage.cocotb",
            config_file=False,
            branch=True,
            source=["cocotb"],
        )
        library_coverage.start()

        def stop_library_coverage() -> None:
            library_coverage.stop()
            library_coverage.save()  # pragma: no cover

        from cocotb import _register_shutdown_callback

        _register_shutdown_callback(stop_library_coverage)
