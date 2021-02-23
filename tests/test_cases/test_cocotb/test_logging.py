# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests for the cocotb logger
"""

import cocotb
import cocotb.log

from common import assert_raises
import logging
import os


class StrCallCounter:
    def __init__(self):
        self.str_counter = 0

    def __str__(self):
        self.str_counter += 1
        return "__str__ called %d time(s)" % self.str_counter


@cocotb.test()
async def test_logging_with_args(dut):
    counter = StrCallCounter()
    dut._log.setLevel(logging.INFO)  # To avoid logging debug message, to make next line run without error
    dut._log.debug("%s", counter)
    assert counter.str_counter == 0

    dut._log.info("%s", counter)
    assert counter.str_counter == 1

    # now try again on the root cocotb logger, which unlike nested loggers
    # is captured
    counter = StrCallCounter()
    cocotb.log.info("%s", counter)
    assert counter.str_counter == 2  # once for stdout, once for captured logs

    dut._log.info("No substitution")

    dut._log.warning("Testing multiple line\nmessage")


@cocotb.test()
async def test_logging_default_config(dut):
    # The cocotb.log module is shadowed by an instance of
    # cocotb.log.SimBaseLog()
    from cocotb.log import default_config as log_default_config

    cocotb_log = logging.getLogger('cocotb')

    # Save pre-test configuration
    log_level_prev = cocotb_log.level
    os_environ_prev = os.environ.copy()

    try:
        # Set a valid log level
        os.environ['COCOTB_LOG_LEVEL'] = 'DEBUG'
        log_default_config()
        assert cocotb_log.level == logging.DEBUG, cocotb_log.level

        # Try to set log level to an invalid log level
        os.environ['COCOTB_LOG_LEVEL'] = 'INVALID_LOG_LEVEL'
        with assert_raises(ValueError):
            log_default_config()

        # Try to set log level to a valid log level with wrong capitalization
        os.environ['COCOTB_LOG_LEVEL'] = 'error'
        log_default_config()
        assert cocotb_log.level == logging.ERROR, cocotb_log.level

    finally:
        # Restore pre-test configuration
        os.environ = os_environ_prev
        cocotb_log.level = log_level_prev


@cocotb.test()
async def test_custom_logging_levels(dut):
    logging.basicConfig(level=logging.NOTSET)
    logging.addLevelName(5, "SUPER_DEBUG")
    logger = logging.getLogger("name")
    logger.setLevel(5)
    logger.log(5, "SUPER DEBUG MESSAGE!")
