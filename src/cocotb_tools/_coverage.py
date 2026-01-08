# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import tempfile
from pathlib import Path

from cocotb_tools import _env


def start_cocotb_library_coverage(_: object) -> None:  # pragma: no cover
    if not _env.as_bool("COCOTB_LIBRARY_COVERAGE"):
        return
    try:
        import coverage  # noqa: PLC0415
    except (ImportError, ModuleNotFoundError):
        raise RuntimeError(
            "cocotb library coverage collection requested but coverage package not available. Install it using `pip install coverage`."
        ) from None
    else:
        tmp_data_file_controller = tempfile.NamedTemporaryFile(
            prefix=".coverage.cocotb.", suffix=".tmp"
        )
        tmp_data_file = tmp_data_file_controller.name
        library_coverage = coverage.coverage(
            data_file=tmp_data_file,
            config_file=False,
            branch=True,
            source=["cocotb"],
        )
        library_coverage.start()

        def stop_library_coverage() -> None:
            try:
                library_coverage.stop()
                library_coverage.save()  # pragma: no cover

                data_file = (
                    getattr(library_coverage.config, "data_file", None)
                    or ".coverage.cocotb"
                )
                data_dir = Path(data_file).resolve().parent
                pattern = data_dir / ".coverage*"
                files = [
                    str(p.resolve())
                    for p in Path(pattern).parent.glob(Path(pattern).name)
                ]

                if files:
                    final_data_file = ".coverage.cocotb"
                    combiner = coverage.coverage(
                        data_file=final_data_file,
                        config_file=False,
                        branch=True,
                        source=["cocotb"],
                    )
                    combiner.combine(data_paths=files, strict=True, keep=True)
            finally:
                tmp_data_file_controller.close()
                Path(tmp_data_file).unlink()

        # This must come after `library_coverage.start()` to ensure coverage is being
        # collected on the cocotb library before importing from it.
        from cocotb._init import _register_shutdown_callback  # noqa: PLC0415

        _register_shutdown_callback(stop_library_coverage)
