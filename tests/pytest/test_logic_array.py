# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import pytest
from cocotb.types import Logic, LogicArray, Range


def test_logic_array_constructor():
    LogicArray([False, 1, "X", Logic("Z")])
    l = LogicArray("01XZ")
    assert all(isinstance(v, Logic) for v in l)
    with pytest.raises(ValueError):
        LogicArray([object()])

    assert LogicArray(range=Range(0, "to", 3)) == LogicArray("XXXX")

    with pytest.raises(TypeError):
        LogicArray(object())

    with pytest.raises(OverflowError):
        LogicArray("101010", Range(0, "to", 0))

    with pytest.raises(ValueError):
        LogicArray()


def test_logic_array_constructor_deprecated():
    with pytest.warns(DeprecationWarning):
        assert LogicArray(0xA7) == LogicArray("10100111")
    with pytest.warns(DeprecationWarning):
        assert LogicArray(10, Range(5, "downto", 0)) == LogicArray("001010")

    with pytest.warns(DeprecationWarning):
        assert LogicArray(-1) == LogicArray("1")
    with pytest.warns(DeprecationWarning):
        assert LogicArray(-2, Range(5, "downto", 0)) == LogicArray("111110")

    with pytest.raises(OverflowError):
        with pytest.warns(DeprecationWarning):
            LogicArray(10, Range(1, "to", 3))
    with pytest.raises(OverflowError):
        with pytest.warns(DeprecationWarning):
            LogicArray(-45, Range(1, "to", 3))


def test_logic_array_int_conversion():
    assert LogicArray.from_unsigned(0xA7) == LogicArray("10100111")
    assert LogicArray.from_unsigned(10, Range(5, "downto", 0)) == LogicArray("001010")
    with pytest.raises(OverflowError):
        LogicArray.from_unsigned(-10)
    with pytest.raises(OverflowError):
        LogicArray.from_unsigned(10, Range(1, "to", 3))

    assert LogicArray.from_signed(-1) == LogicArray("1")
    assert LogicArray.from_signed(-2, Range(5, "downto", 0)) == LogicArray("111110")
    with pytest.raises(OverflowError):
        LogicArray.from_signed(-45, Range(1, "to", 3))


def test_logic_array_properties():
    assert LogicArray("01").is_resolvable
    assert not LogicArray("1X1").is_resolvable


def test_logic_array_properties_deprecated():
    with pytest.warns(DeprecationWarning):
        assert LogicArray(0).integer == 0
    with pytest.warns(DeprecationWarning):
        assert LogicArray(0).signed_integer == 0
    with pytest.warns(DeprecationWarning):
        assert LogicArray(0).binstr == "0"
    with pytest.warns(DeprecationWarning):
        assert LogicArray(10).integer == 10
    with pytest.warns(DeprecationWarning):
        assert LogicArray(10).signed_integer == -6
    with pytest.warns(DeprecationWarning):
        assert LogicArray(10).binstr == "1010"
    with pytest.warns(DeprecationWarning):
        assert LogicArray(-6).integer == 10
    with pytest.warns(DeprecationWarning):
        assert LogicArray(-6).signed_integer == -6
    with pytest.warns(DeprecationWarning):
        assert LogicArray(-6).binstr == "1010"


def test_logic_array_setattr():
    l = LogicArray("0000")
    l[1] = "X"
    assert l == LogicArray("00X0")
    with pytest.raises(TypeError):
        l[object()] = "X"


def test_logic_array_repr():
    l = LogicArray("1XX110")
    assert eval(repr(l)) == l


def test_logic_array_and():
    l = LogicArray("0011XZ")
    p = LogicArray("011010")
    assert (l & p) == LogicArray("0010X0")
    with pytest.raises(TypeError):
        l & object()
    with pytest.raises(TypeError):
        object() & l
    with pytest.raises(ValueError):
        LogicArray("") & LogicArray("01")


def test_logic_array_or():
    l = LogicArray("0011XZ")
    p = LogicArray("011010", Range(-9, "downto", -14))
    assert (l | p) == LogicArray("01111X")
    with pytest.raises(TypeError):
        l | object()
    with pytest.raises(TypeError):
        object() | l
    with pytest.raises(ValueError):
        LogicArray("") | LogicArray("01")


def test_logic_array_xor():
    l = LogicArray("0011XZ")
    p = LogicArray("011010")
    assert (l ^ p) == LogicArray("0101XX")
    with pytest.raises(TypeError):
        l ^ object()
    with pytest.raises(TypeError):
        object() ^ l
    with pytest.raises(ValueError):
        LogicArray("") ^ LogicArray("01")


def test_logic_array_invert():
    assert ~LogicArray("01XZ") == LogicArray("10XX")


def test_logic_array_literal_casts():
    assert str(LogicArray("UX01ZWLH-")) == "UX01ZWLH-"
    assert int(LogicArray("0101010")) == 0b0101010


def test_equality():
    # fmt: off
    assert LogicArray("0101", Range(0, 'to', 3)) == LogicArray("0101", Range(0, 'to', 3))
    assert LogicArray("0101", Range(0, 'to', 3)) == LogicArray("0101", Range(7, 'downto', 4))
    assert LogicArray("0101", Range(0, 'to', 3)) != LogicArray("1010", Range(0, 'to', 3))
    # fmt: on
    assert LogicArray("0101") == "0101"
    assert LogicArray("0101") == [0, 1, 0, 1]
    assert LogicArray("0101") == 0b0101
    assert LogicArray("XXXX") != 1
    assert LogicArray("0101") != object()
    assert LogicArray("0101") != "lol"
    assert LogicArray("0101") != 123


def test_repr_eval():
    r = LogicArray("X01Z")
    assert eval(repr(r)) == r


def test_iter():
    val = [Logic(0), Logic(1), Logic("X"), Logic("Z")]
    a = LogicArray(val)
    assert list(a) == val


def test_reversed():
    val = [Logic(0), Logic(1), Logic("X"), Logic("Z")]
    a = LogicArray(val)
    assert list(reversed(a)) == list(reversed(val))


def test_contains():
    a = LogicArray("01XZ")
    assert Logic("X") in a
    assert Logic("U") not in a


def test_index():
    r = LogicArray("0001101", Range(7, "downto", 1))
    assert r.index(Logic("1")) == 4
    assert r.index(Logic("1"), 2, 0) == 1
    with pytest.raises(IndexError):
        r.index(object())


def test_count():
    assert LogicArray("011X1Z").count(Logic("1")) == 3


def test_indexing():
    a = LogicArray("0101", Range(8, "to", 11))
    assert a[8] == "0"
    with pytest.raises(IndexError):
        a[0]
    a[11] = "X"
    assert a[11] == "X"

    b = LogicArray("Z01X", Range(10, "downto", 7))
    assert b[8] == 1
    with pytest.raises(IndexError):
        b[-2]
    b[8] = 0
    assert b[8] == 0


def test_bad_indexing():
    with pytest.raises(TypeError):
        LogicArray("01XZ")[list()]
    with pytest.raises(TypeError):
        LogicArray("1010")[object()] = 9


def test_slicing():
    a = LogicArray("0110XXUU")
    b = a[5:1]
    assert b.left == 5
    assert b.right == 1
    assert b == LogicArray("10XXU")
    a[3:0] = "ZZZZ"
    assert a == LogicArray("0110ZZZZ")


def test_slicing_infered_start_stop():
    a = LogicArray("XXXX")
    assert a[:] == a
    a[:] = "1010"
    assert a == 0b1010


def test_dont_specify_step():
    with pytest.raises(IndexError):
        LogicArray("1010")[::1]
    with pytest.raises(IndexError):
        LogicArray("1010")[1:2:1] = [1, 2]


def test_slice_direction_mismatch():
    a = LogicArray("1010", Range(10, "downto", 7))
    with pytest.raises(IndexError):
        a[7:9]
    with pytest.raises(IndexError):
        a[9:10] = "01"


def test_set_slice_wrong_length():
    a = LogicArray("XXXXXX")
    with pytest.raises(ValueError):
        a[4:2] = "0000000000000"


def test_slice_correct_infered():
    a = LogicArray("1111")
    b = a[:3]
    assert b.right == 3


def test_changing_range():
    a = LogicArray("X01Z")
    a.range = Range(3, "downto", 0)
    assert a.range == Range(3, "downto", 0)
    with pytest.raises(TypeError):
        a.range = range(10)
    with pytest.raises(ValueError):
        a.range = Range(7, "downto", 0)
