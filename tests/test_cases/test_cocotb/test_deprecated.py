import cocotb
import warnings
from contextlib import contextmanager


@contextmanager
def assert_deprecated():
    warns = []
    try:
        with warnings.catch_warnings(record=True) as warns:
            # Cause all warnings to always be triggered.
            warnings.simplefilter("always")
            yield warns  # note: not a cocotb yield, but a contextlib one!
    finally:
        assert len(warns) == 1
        assert issubclass(warns[0].category, DeprecationWarning)


@cocotb.test()
async def test_returnvalue_deprecated(dut):

    @cocotb.coroutine
    def get_value():
        yield cocotb.triggers.Timer(1, units='ns')
        raise cocotb.result.ReturnValue(42)

    with assert_deprecated() as warns:
        val = await get_value()
    assert val == 42
    assert "return statement instead" in str(warns[0].message)


# strings are not supported on Icarus
@cocotb.test(skip=cocotb.SIM_NAME.lower().startswith("icarus"))
async def test_unicode_handle_assignment_deprecated(dut):
    with assert_deprecated() as warns:
        dut.string_input_port <= "Bad idea"
    assert "bytes" in str(warns[0].message)
