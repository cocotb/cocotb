# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import contextlib
import logging
from collections.abc import Generator

import cocotb
from cocotb.logging import ANSI


class LogCaptureData:
    def __init__(self) -> None:
        self.records: list[logging.LogRecord] = []
        self.msgs: list[str] = []


@contextlib.contextmanager
def capture_logs(handler: logging.Handler) -> Generator[LogCaptureData, None, None]:
    data = LogCaptureData()

    old_emit = handler.emit

    def emit(record: logging.LogRecord) -> None:
        data.records.append(record)
        data.msgs.append(handler.format(record))
        old_emit(record)

    handler.emit = emit  # type: ignore[method-assign]
    try:
        yield data
    finally:
        handler.emit = old_emit  # type: ignore[method-assign]


@cocotb.test
async def test_log_prefix_custom(_: object) -> None:
    logger = logging.getLogger("example")
    logger.setLevel(logging.INFO)
    with capture_logs(logging.getLogger().handlers[0]) as logs:
        logger.info("Test log message")
    assert (
        logs.msgs[0]
        == f"{ANSI.YELLOW_FG}abc{ANSI.DEFAULT_FG} INFO 0       exam Test log message{ANSI.DEFAULT}"
    )


@cocotb.test
async def test_log_prefix_default(_: object) -> None:
    logger = logging.getLogger("example")
    logger.setLevel(logging.INFO)
    with capture_logs(logging.getLogger().handlers[0]) as logs:
        logger.warning("First line\nsecond line")
        cocotb.logging.strip_ansi = True
        logger.warning("First line\nsecond line")

    lines_colored = logs.msgs[0].splitlines()
    assert len(lines_colored) == 2
    assert lines_colored[0].endswith("First line")
    assert lines_colored[1].endswith(f"second line{ANSI.DEFAULT}")

    lines_stripped = logs.msgs[1].splitlines()
    assert len(lines_stripped) == 2
    assert lines_stripped[0].endswith("First line")
    assert lines_stripped[1].endswith("second line")

    assert lines_stripped[0].find("First line") == lines_stripped[1].find("second line")
    assert lines_colored[1].find("second line") == lines_stripped[1].find("second line")
