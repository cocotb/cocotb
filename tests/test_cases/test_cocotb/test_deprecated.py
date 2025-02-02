# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import os
import warnings

import pytest

import cocotb
from cocotb.regression import TestFactory
from cocotb.triggers import Edge, Event, First, Join, Timer

LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()


# identifiers starting with `_` are illegal in VHDL
@cocotb.test(skip=LANGUAGE in ("vhdl"))
async def test_id_deprecated(dut):
    with pytest.warns(DeprecationWarning):
        dut._id("_underscore_name", extended=False)


test_testfactory_deprecated_values = []


async def test_testfactory_deprecated_test(dut, a):
    test_testfactory_deprecated_values.append(a)


with warnings.catch_warnings(record=True) as tf_warns:
    warnings.simplefilter("default", category=DeprecationWarning)
    tf = TestFactory(test_testfactory_deprecated_test)

tf.add_option("a", [1, 2])
tf.generate_tests()


@cocotb.test
async def test_testfactory_deprecated(dut):
    assert "test_testfactory_deprecated_test_001" in globals()
    assert "test_testfactory_deprecated_test_002" in globals()
    assert test_testfactory_deprecated_values == [1, 2]
    assert len(tf_warns) == 1
    assert tf_warns[0].category is DeprecationWarning


@cocotb.test(skip=cocotb.SIM_NAME.lower().startswith(("icarus", "ghdl")))
async def test_real_handle_casts_deprecated(dut):
    dut.stream_in_real.value = 5.03
    await Timer(1, "ns")
    with pytest.warns(DeprecationWarning):
        assert float(dut.stream_in_real) == 5.03


@cocotb.test(skip=cocotb.SIM_NAME.lower().startswith("icarus"))
async def test_int_handle_casts_deprecated(dut):
    dut.stream_in_int.value = 100
    await Timer(1, "ns")
    with pytest.warns(DeprecationWarning):
        assert int(dut.stream_in_int) == 100


@cocotb.test
async def test_logic_handle_casts_deprecated(dut):
    dut.stream_in_data.value = 0b1011_0011
    await Timer(1, "ns")
    with pytest.warns(DeprecationWarning):
        assert int(dut.stream_in_data) == 0b1011_0011
    with pytest.warns(DeprecationWarning):
        assert str(dut.stream_in_data) == "10110011"


@cocotb.test(skip=cocotb.SIM_NAME.lower().startswith(("icarus", "ghdl")))
async def test_string_handle_casts_deprecated(dut):
    dut.stream_in_string.value = b"sample"
    await Timer(1, "ns")
    with pytest.warns(DeprecationWarning):
        str(dut.stream_in_string)


@cocotb.test
async def test_join_trigger_deprecated(_) -> None:
    async def returns_1():
        return 1

    t = cocotb.start_soon(returns_1())
    with pytest.warns(DeprecationWarning, match=r"Join\(task\)"):
        j = Join(t)
    assert (await j) == 1


@cocotb.test
async def test_join_trigger_in_first_backwards_compat(_) -> None:
    async def returns_1():
        return 1

    t = cocotb.start_soon(returns_1())
    with pytest.warns(DeprecationWarning, match=r"Join\(task\)"):
        j = Join(t)
    res = await First(j, Timer(1))
    assert res == 1


@cocotb.test
async def test_task_join_deprecated(_) -> None:
    async def returns_1():
        return 1

    t = cocotb.start_soon(returns_1())
    with pytest.warns(DeprecationWarning, match=r"task.join\(\)"):
        j = t.join()
    assert (await j) == 1


@cocotb.test
async def test_task_join_in_first_backwards_compat(_) -> None:
    async def returns_1():
        return 1

    t = cocotb.start_soon(returns_1())
    with pytest.warns(DeprecationWarning, match=r"task.join\(\)"):
        j = t.join()
    res = await First(j, Timer(1))
    assert res == 1


@cocotb.test
async def test_event_data_deprecated(_) -> None:
    e = Event()

    with pytest.warns(DeprecationWarning):
        e.data = 12

    with pytest.warns(DeprecationWarning):
        assert e.data == 12

    with pytest.warns(DeprecationWarning):
        e.set(42)

    with pytest.warns(DeprecationWarning):
        assert e.data == 42


@cocotb.test
async def test_logic_scalar_object_methods_deprecated(dut) -> None:
    dut.stream_in_valid.value = 1
    await Timer(1, "ns")
    with pytest.warns(DeprecationWarning):
        assert int(dut.stream_in_valid) == 1
    with pytest.warns(DeprecationWarning):
        assert str(dut.stream_in_valid) == "1"
    with pytest.warns(DeprecationWarning):
        assert len(dut.stream_in_valid) == 1


@cocotb.test
async def test_edge_trigger_deprecated(dut) -> None:
    with pytest.warns(DeprecationWarning):
        e = Edge(dut.stream_in_valid)
    assert e is dut.stream_in_valid.value_change
