# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import logging
import re
from pathlib import Path

import pytest
from test_cocotb import (
    compile_args,
    gpi_interfaces,
    hdl_toplevel,
    hdl_toplevel_lang,
    sim,
    sim_args,
    sources,
    tests_dir,
)

from cocotb_tools.runner import get_runner

pytestmark = pytest.mark.simulator_required

REGRESSION_LOG = "regression.log"


def configure_logging() -> None:
    """PYGPI_USERS entry point capturing regression output inside the simulator."""
    # Proprietary simulator CI redacts stdout, so write Python logs directly.
    handler = logging.FileHandler(REGRESSION_LOG, mode="w", encoding="utf-8")
    logging.getLogger("cocotb.regression").addHandler(handler)


def test_xfail_results_without_preview(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Without preview, expected failures still report PASS in the summary."""
    monkeypatch.delenv("COCOTB_PREVIEW", raising=False)
    monkeypatch.setenv("COCOTB_ANSI_OUTPUT", "0")
    monkeypatch.setenv(
        "PYGPI_USERS",
        "cocotb_tools._coverage:start_cocotb_library_coverage,"
        "cocotb.logging:_configure,"
        "cocotb._init:init_package_from_simulation,"
        "test_no_previews:configure_logging,"
        "cocotb.regression:_run_regression",
    )
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parent))
    monkeypatch.syspath_prepend(str(tests_dir / "test_cases" / "test_xfail"))

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel=hdl_toplevel,
        build_dir=tmp_path,
        build_args=compile_args,
    )
    runner.test(
        hdl_toplevel_lang=hdl_toplevel_lang,
        hdl_toplevel=hdl_toplevel,
        test_module="test_xfail",
        testcase="test_xfail",
        gpi_interfaces=gpi_interfaces,
        test_args=sim_args,
    )

    log = (tmp_path / REGRESSION_LOG).read_text(encoding="utf-8")
    assert re.search(r"\*\* test_xfail\.test_xfail\s+PASS\s+", log)
    assert "TESTS=1 PASS=1 FAIL=0 SKIP=0" in log
    assert "XFAIL" not in log
