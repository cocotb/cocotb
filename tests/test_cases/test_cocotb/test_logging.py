# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests for the cocotb logger
"""

import contextlib
import logging
import warnings
from typing import Generator, Union

import cocotb
import cocotb._ANSI as ansi
import cocotb.logging as cocotb_logging


class LogCaptureHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []
        self.msgs: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)
        msg = self.format(record)
        self.msgs.append(msg)


@contextlib.contextmanager
def capture_logs(
    logger_name: Union[str, None] = None,
    formatter: Union[logging.Formatter, None] = None,
) -> Generator[LogCaptureHandler, None, None]:
    handler = LogCaptureHandler()
    if formatter is None:
        formatter = cocotb_logging.SimLogFormatter()
    handler.setFormatter(formatter)
    logger = logging.getLogger(logger_name)
    logger.addHandler(handler)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)


class StrCallCounter:
    def __init__(self):
        self.str_counter = 0

    def __str__(self):
        self.str_counter += 1
        return f"__str__ called {self.str_counter} time(s)"


@cocotb.test()
async def test_logging_with_args(dut):
    counter = StrCallCounter()
    dut._log.setLevel(
        logging.INFO
    )  # To avoid logging debug message, to make next line run without error
    dut._log.debug("%s", counter)
    assert counter.str_counter == 0

    dut._log.info("%s", counter)
    assert counter.str_counter == 1

    dut._log.info("No substitution")

    dut._log.warning("Testing multiple line\nmessage")


@cocotb.test()
async def test_custom_logging_levels(dut):
    logging.basicConfig(level=logging.NOTSET)
    logging.addLevelName(5, "SUPER_DEBUG")
    logger = logging.getLogger("name")
    logger.setLevel(5)
    with capture_logs() as logs:
        logger.log(5, "SUPER DEBUG MESSAGE!")
    assert len(logs.msgs) == 1
    assert "SUPER DEBUG MESSAGE!" in logs.msgs[0]


@cocotb.test
async def test_ansi_stripping(_: object) -> None:
    cocotb_logging.strip_ansi = True
    with capture_logs() as logs:
        cocotb.log.info(
            f"{ansi.YELLOW_FG}That {ansi.GREEN_BG}boy {ansi.BLUE_FG}ain't {ansi.BRIGHT_RED_BG}right.{ansi.DEFAULT_FG}"
        )
    assert len(logs.msgs) == 1
    assert logs.msgs[0].endswith("That boy ain't right.")


@cocotb.test
async def test_warning_capture(_: object) -> None:
    with warnings.catch_warnings(), capture_logs() as logs:
        warnings.simplefilter("always")
        warnings.warn("This is a test warning", UserWarning)
    assert len(logs.msgs) == 1
    assert "This is a test warning" in logs.msgs[0]
