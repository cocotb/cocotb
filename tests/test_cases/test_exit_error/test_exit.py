import cocotb
from cocotb.triggers import Timer


@cocotb.test()
async def test_name_error(_):
    # this syntax error makes the whole file unimportable, so the file contents
    # don't really matter.
    await Timer(100, "ns")


NameErrorLol  # noqa: F821
