# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests for the cocotb logger
"""
import cocotb
from cocotb.triggers import Timer
import logging


class StrCallCounter(object):
    def __init__(self):
        self.str_counter = 0

    def __str__(self):
        self.str_counter += 1
        return "__str__ called %d time(s)" % self.str_counter


@cocotb.test()
def test_logging_with_args(dut):
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

    yield Timer(100)  # Make it do something with time
