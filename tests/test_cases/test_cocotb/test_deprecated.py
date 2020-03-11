import cocotb
import warnings


@cocotb.test()
async def test_returnvalue_deprecated(dut):
    @cocotb.coroutine
    def get_value():
        yield cocotb.triggers.Timer(1, units='ns')
        raise cocotb.result.ReturnValue(42)

    with warnings.catch_warnings(record=True) as w:
        # Cause all warnings to always be triggered.
        warnings.simplefilter("always")
        val = await get_value()
    assert val == 42
    assert len(w) == 1
    assert issubclass(w[-1].category, DeprecationWarning)
    assert "return statement instead" in str(w[-1].message)
