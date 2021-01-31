"""
Test that cocotb doesn't die if a new logging level is added
"""
import cocotb
import logging


@cocotb.test()
async def test_alu(dut):
    logging.basicConfig(level=logging.NOTSET)
    logging.addLevelName(5, "SUPER_DEBUG")
    logger = logging.getLogger("name")
    logger.setLevel(5)
    logger.log(5, "SUPER DEBUG MESSAGE!")
