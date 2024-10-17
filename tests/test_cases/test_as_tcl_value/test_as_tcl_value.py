import cocotb
from cocotb.runner import as_tcl_value

@cocotb.test()
async def test_empty_string(dut):
  assert as_tcl_value("") == ""

@cocotb.test()
async def test_special_char(dut):
  assert as_tcl_value("Test \n end\ttest\r") == "Test\\ \\n\\ end\\\ttest\\\r"
