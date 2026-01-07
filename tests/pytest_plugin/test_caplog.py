# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test pytest `caplog` fixture."""

from __future__ import annotations

from logging import INFO, WARNING, Logger, getLogger

from pytest import LogCaptureFixture


async def test_capture_info(dut, caplog: LogCaptureFixture) -> None:
    """Test capturing informational logs."""
    caplog.set_level(INFO, logger="test")
    logger: Logger = getLogger("test")

    expected: str = "Message to be captured"
    logger.info(expected)

    assert expected in caplog.text


async def test_capture_warning(dut, caplog: LogCaptureFixture) -> None:
    """Test capturing warning logs."""
    caplog.set_level(WARNING, logger="test")
    logger: Logger = getLogger("test")

    unexpected: str = "Unexpected message not to be captured"
    expected: str = "Warning to be captured"

    logger.info(unexpected)
    logger.warning(expected)

    assert expected in caplog.text
    assert unexpected not in caplog.text
