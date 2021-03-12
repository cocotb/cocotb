# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

"""Example of a custom logger class and a test showing its usage."""

import cocotb
from cocotb.log import SimColourLogFormatter, get_time_from_sim_steps
from cocotb.triggers import Timer

import logging
import random


class CustomLogFormatter(SimColourLogFormatter):
    """Example of a custom log formatter class.

    Changes compared to the default logger are:
    * Prints timestamps in microseconds.
    * Prints a vertical "bracket" highlighting timestamp changes:
      * a "├" in the leftmost column if the current timestamp is different from the previous one, and
      * a "│" in the leftmost column if the current timestamp is the same as the previous one.
    """

    def __init__(self):
        super().__init__()
        self.sim_time_str_old = None

    def _format_sim_time(self, record, time_chars=12, time_base="us"):
        sim_time = getattr(record, "created_sim_time", None)
        if sim_time is None:
            sim_time_str = "  -.--{}".format(time_base)
        else:
            time_with_base = get_time_from_sim_steps(sim_time, time_base)
            sim_time_str = "{:4.4f}{}".format(time_with_base, time_base)
        if sim_time_str != self.sim_time_str_old:
            self.sim_time_str_old = sim_time_str
            return "".join(["├", sim_time_str.rjust(time_chars)])
        else:
            return "".join(["│", sim_time_str.rjust(time_chars)])


async def do_log(dut):
    for timestep in range(10):
        rand_wait = random.randrange(7)
        await Timer(1, "ns")
        for idx_msg in range(rand_wait):
            dut._log.info("timestep %s, msg %s", timestep, idx_msg)


@cocotb.test()
async def test_custom_logger(dut):
    """Test the custom logger."""

    fmt = CustomLogFormatter()
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.setFormatter(fmt)

    await do_log(dut)

    # some sanity checks for the example, you don't need this in user code

    # print("_format_recordname:", fmt._format_recordname.cache_info())
    # print("_format_filename:", fmt._format_filename.cache_info())
    # print("_format_funcname:", fmt._format_funcname.cache_info())
    assert (
        fmt._format_recordname.cache_info().hits > 0
    ), "Nothing was taken from the _format_recordname LRU cache"
    assert (
        fmt._format_filename.cache_info().hits > 0
    ), "Nothing was taken from the _format_filename LRU cache"
    assert (
        fmt._format_funcname.cache_info().hits > 0
    ), "Nothing was taken from the _format_funcname LRU cache"
