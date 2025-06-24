# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import os


def start_cocotb_library_coverage(_: object) -> None:  # pragma: no cover
    if "COCOTB_LIBRARY_COVERAGE" not in os.environ:
        return
    try:
        import coverage  # noqa: PLC0415
    except (ImportError, ModuleNotFoundError):
        raise RuntimeError(
            "cocotb library coverage collection requested but coverage package not available. Install it using `pip install coverage`."
        ) from None
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

        # This must come after `library_coverage.start()` to ensure coverage is being
        # collected on the cocotb library before importing from it.
        from cocotb._init import _register_shutdown_callback  # noqa: PLC0415

        _register_shutdown_callback(stop_library_coverage)
