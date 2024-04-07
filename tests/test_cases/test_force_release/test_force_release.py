import cocotb
from cocotb.clock import Clock
from cocotb.handle import Force, Release
from cocotb.triggers import ClockCycles, Timer


@cocotb.test(expect_fail=cocotb.SIM_NAME.lower().startswith(("ghdl", "verilator")))
async def test_hdl_writes_dont_overwrite_force_combo(dut):
    """Test Forcing then later Releasing a combo signal."""

    dut.stream_in_data.value = 4

    # Force the driven signal.
    dut.stream_out_data_comb.value = Force(5)
    await Timer(10, "ns")
    assert dut.stream_out_data_comb.value == 5

    # Release the driven signal.
    # The driver signal is set again to trigger the process which recomputes the driven signal
    # This is done because releasing the driven signal does not cause the process to run again.
    dut.stream_in_data.value = 3
    dut.stream_out_data_comb.value = Release()
    await Timer(10, "ns")
    assert dut.stream_out_data_comb.value == 3


@cocotb.test(expect_fail=cocotb.SIM_NAME.lower().startswith(("ghdl", "verilator")))
async def test_hdl_writes_dont_overwrite_force_registered(dut):
    """Test Forcing then Releasing a registered output."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    dut.stream_in_data.value = 4

    # Force the driven signal.
    dut.stream_out_data_registered.value = Force(5)
    await ClockCycles(dut.clk, 2)
    assert dut.stream_out_data_registered.value == 5

    # Release the driven signal.
    dut.stream_out_data_registered.value = Release()
    await ClockCycles(dut.clk, 2)
    assert dut.stream_out_data_registered.value == 4


@cocotb.test(expect_fail=cocotb.SIM_NAME.lower().startswith("ghdl"))
async def test_force_followed_by_release_combo(dut):
    """Test if Force followed immediately by Release works on combo signals."""

    dut.stream_in_data.value = 14

    # Force driven signal then immediately release it.
    dut.stream_out_data_comb.value = Force(23)
    dut.stream_out_data_comb.value = Release()

    # Check if the driven signal is actually released.
    # The driver signal is set again to trigger the process which recomputes the driven signal
    # This is done because releasing the driven signal does not cause the process to run again.
    dut.stream_in_data.value = 16
    await Timer(10, "ns")
    assert dut.stream_out_data_comb.value == 16


@cocotb.test(expect_fail=cocotb.SIM_NAME.lower().startswith("ghdl"))
async def test_force_followed_by_release_registered(dut):
    """Test if Force followed immediately by Release works on registered signals."""

    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    dut.stream_in_data.value = 90

    # Force driven signal then immediately release it.
    dut.stream_out_data_registered.value = Force(5)
    dut.stream_out_data_registered.value = Release()

    # Check if the driven signal is actually released.
    await ClockCycles(dut.clk, 2)
    assert dut.stream_out_data_registered.value == 90


@cocotb.test(expect_fail=cocotb.SIM_NAME.lower().startswith(("ghdl", "verilator")))
async def test_cocotb_writes_dont_overwrite_force_combo(dut):
    """Test Deposits following a Force don't overwrite the value."""
    dut.stream_in_data.value = 56

    # Force the driven signal.
    dut.stream_out_data_comb.value = Force(10)
    await Timer(10, "ns")
    assert dut.stream_out_data_comb.value == 10

    # Attempt depositing on the forced signal. This shouldn't change the value.
    dut.stream_out_data_comb.value = 11
    await Timer(10, "ns")
    assert dut.stream_out_data_comb.value == 10

    # Release the forced signal. The value should follow driver.
    # The driver signal is set again to trigger the process which recomputes the driven signal
    # This is done because releasing the driven signal does not cause the process to run again.
    dut.stream_in_data.value = 46
    dut.stream_out_data_registered.value = Release()
    await Timer(10, "ns")
    assert dut.stream_in_data.value == 46


@cocotb.test(expect_fail=cocotb.SIM_NAME.lower().startswith(("ghdl", "verilator")))
async def test_cocotb_writes_dont_overwrite_force_registered(dut):
    """Test Deposits following a Force don't overwrite the value."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    dut.stream_in_data.value = 77

    # Force the driven signal.
    dut.stream_out_data_registered.value = Force(10)
    await ClockCycles(dut.clk, 2)
    assert dut.stream_out_data_registered.value == 10

    # Attempt depositing on the forced signal. This shouldn't change the value.
    dut.stream_out_data_registered.value = 11
    await ClockCycles(dut.clk, 2)
    assert dut.stream_out_data_registered.value == 10

    # Release the forced signal. The value should follow driver.
    dut.stream_out_data_registered.value = Release()
    await ClockCycles(dut.clk, 2)
    assert dut.stream_in_data.value == 77


@cocotb.test(expect_fail=True)
async def test_force_followed_by_release_correct_value(dut):
    """Tests if Forcing then immediately Releasing a signal yield the correct value.

    Due to the way that Release and Freeze are implemented (reading the current value then doing a set with that value) this test will always fail.
    Leaving this test for when a better implementation of Freeze and Release are implemented.
    """
    dut.stream_in_data.value = 19
    await Timer(10, "ns")
    assert dut.stream_in_data.value == 19

    dut.stream_in_data.value = Force(0)
    dut.stream_in_data.value = Release()
    await Timer(10, "ns")
    assert dut.stream_in_data.value == 0
