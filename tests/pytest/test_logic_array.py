# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import copy

import pytest

from cocotb.types import Logic, LogicArray, Range


def test_logic_array_str_construction():
    LogicArray("01XZ")
    assert LogicArray("1010", Range(0, "to", 3)) == LogicArray("1010")
    assert LogicArray("1010", 4) == LogicArray("1010")
    assert LogicArray("1010", range=Range(0, "to", 3)) == LogicArray("1010")

    with pytest.raises(ValueError):
        LogicArray("101010", Range(0, "to", 0))

    with pytest.raises(ValueError):
        LogicArray("5h7_@")


def test_logic_array_iterable_construction():
    assert LogicArray([False, 1, "X", Logic("Z")]) == LogicArray("01XZ")
    assert LogicArray((1, 0, 1, 0), Range(0, "to", 3)) == LogicArray("1010")
    assert LogicArray((1, 0, 1, 0), 4) == LogicArray("1010")
    assert LogicArray((1, 0, 1, 0), range=Range(0, "to", 3)) == LogicArray("1010")

    def gen():
        yield True
        yield 0
        yield "X"
        yield Logic("Z")

    assert LogicArray(gen()) == LogicArray("10XZ")

    with pytest.raises(ValueError):
        LogicArray([1, 0, 1, 0], Range(1, "downto", 0))
    with pytest.raises(ValueError):
        LogicArray(["l", "o", "l"])
    with pytest.raises(TypeError):
        LogicArray([object()])


def test_logic_array_int_construction():
    with pytest.raises(TypeError):
        LogicArray(10)  # refuse temptation to guess
    assert LogicArray(10, Range(5, "downto", 0)) == LogicArray("001010")
    assert LogicArray(10, 6) == LogicArray("001010")
    assert LogicArray(10, range=Range(5, "downto", 0)) == LogicArray("001010")

    with pytest.raises(ValueError):
        LogicArray(10, Range(1, "to", 3))
    with pytest.raises(ValueError):
        LogicArray(-10, Range(7, "downto", 0))


def test_logic_array_bad_construction():
    with pytest.raises(TypeError):
        LogicArray(object())
    with pytest.raises(TypeError):
        LogicArray("1010", {})
    with pytest.raises(TypeError):
        LogicArray(range={})
    with pytest.raises(TypeError):
        LogicArray()


def test_logic_array_unsigned_conversion():
    with pytest.raises(TypeError):
        LogicArray.from_unsigned(10)  # refuse temptation to guess
    assert LogicArray.from_unsigned(10, Range(5, "downto", 0)) == LogicArray("001010")
    assert LogicArray.from_unsigned(10, 6) == LogicArray("001010")
    assert LogicArray.from_unsigned(10, range=Range(5, "downto", 0)) == LogicArray(
        "001010"
    )

    with pytest.raises(ValueError):
        LogicArray.from_unsigned(10, Range(1, "to", 3))
    with pytest.raises(ValueError):
        LogicArray.from_unsigned(10, 3)

    with pytest.raises(ValueError):
        LogicArray.from_unsigned(-10, Range(7, "downto", 0))

    with pytest.raises(TypeError):
        LogicArray.from_unsigned(object(), Range(3, "downto", 0))
    with pytest.raises(TypeError):
        LogicArray.from_unsigned(10, "lol")


def test_logic_array_signed_conversion():
    with pytest.raises(TypeError):
        LogicArray.from_signed(-2)  # refuse temptation to guess
    assert LogicArray.from_signed(-2, Range(5, "downto", 0)) == LogicArray("111110")
    assert LogicArray.from_signed(-2, 6) == LogicArray("111110")
    assert LogicArray.from_signed(-2, range=Range(5, "downto", 0)) == LogicArray(
        "111110"
    )

    with pytest.raises(ValueError):
        LogicArray.from_signed(-45, Range(1, "to", 3))
    with pytest.raises(ValueError):
        LogicArray.from_signed(-45, 3)

    with pytest.raises(TypeError):
        LogicArray.from_signed(object(), Range(3, "downto", 0))
    with pytest.raises(TypeError):
        LogicArray.from_signed(10, "lol")

    with pytest.raises(ValueError):
        LogicArray.from_signed(-9, 4)
    assert LogicArray.from_signed(-8, 4) == LogicArray("1000")
    assert LogicArray.from_signed(7, 4) == LogicArray("0111")
    with pytest.raises(ValueError):
        LogicArray.from_signed(8, 4)


def test_logic_array_bytes_conversion():
    assert LogicArray.from_bytes(b"12", byteorder="big") == LogicArray(
        "0011000100110010"
    )

    with pytest.raises(ValueError):
        LogicArray.from_bytes(b"123", Range(6, "downto", 0), byteorder="big")
    with pytest.raises(ValueError):
        LogicArray.from_bytes(b"123", 10, byteorder="big")

    # b"1" would fit in a 7 bit LogicArray, but we do not guess if top bits are significant or not
    with pytest.raises(ValueError):
        LogicArray.from_bytes(b"1", Range(6, "downto", 0), byteorder="big")

    assert LogicArray("00101010").to_bytes(byteorder="big") == b"\x2a"


def test_logic_array_properties():
    assert LogicArray("01").is_resolvable
    assert not LogicArray("1X1").is_resolvable


def test_logic_array_properties_deprecated():
    with pytest.warns(DeprecationWarning):
        assert LogicArray("1010").integer == 10

    l = LogicArray("1100")
    with pytest.warns(DeprecationWarning):
        l.integer = 1
    assert l.to_unsigned() == 1
    with pytest.warns(DeprecationWarning), pytest.raises(ValueError):
        l.integer = 100
    with pytest.warns(DeprecationWarning), pytest.raises(ValueError):
        l.integer = -1

    with pytest.warns(DeprecationWarning):
        assert LogicArray("1010").signed_integer == -6

    l = LogicArray("1100")
    with pytest.warns(DeprecationWarning):
        l.signed_integer = 3
    assert l.to_signed() == 3
    with pytest.warns(DeprecationWarning):
        l.signed_integer = -1
    assert l.to_signed() == -1
    with pytest.warns(DeprecationWarning), pytest.raises(ValueError):
        l.signed_integer = 100
    with pytest.warns(DeprecationWarning), pytest.raises(ValueError):
        l.signed_integer = -10

    with pytest.warns(DeprecationWarning):
        assert LogicArray("1010").binstr == "1010"

    l = LogicArray("1010")
    with pytest.warns(DeprecationWarning):
        l.binstr = "0101"
    assert str(l) == "0101"

    with pytest.warns(DeprecationWarning):
        assert LogicArray("01000001" + "00101111").buff == b"\x41\x2f"

    l = LogicArray("0" * 16)
    with pytest.warns(DeprecationWarning):
        l.buff = b"\x41\x2f"
    assert l.to_bytes(byteorder="big") == b"\x41\x2f"
    with pytest.warns(DeprecationWarning), pytest.raises(ValueError):
        l.buff = b"\x41\x2f0123"
    with pytest.warns(DeprecationWarning), pytest.raises(ValueError):
        l.buff = b""


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


def test_logic_array_index_casts():
    assert bin(LogicArray("000101")) == "0b101"
    assert hex(LogicArray("01111010")) == "0x7a"
    with pytest.raises(ValueError):
        bin(LogicArray("X010"))


def test_equality():
    # fmt: off
    # cross product of all impls
    assert LogicArray("0101", Range(0, 'to', 3)) == LogicArray("0101", Range(0, 'to', 3))
    assert LogicArray("0101", Range(0, 'to', 3)) == LogicArray(0b0101, Range(0, 'to', 3))
    assert LogicArray("0101", Range(0, 'to', 3)) == LogicArray([0, 1, 0, 1], Range(0, 'to', 3))
    assert LogicArray(0b0101, Range(0, 'to', 3)) == LogicArray("0101", Range(0, 'to', 3))
    assert LogicArray(0b0101, Range(0, 'to', 3)) == LogicArray(0b0101, Range(0, 'to', 3))
    assert LogicArray(0b0101, Range(0, 'to', 3)) == LogicArray([0, 1, 0, 1], Range(0, 'to', 3))
    assert LogicArray([0, 1, 0, 1], Range(0, 'to', 3)) == LogicArray("0101", Range(0, 'to', 3))
    assert LogicArray([0, 1, 0, 1], Range(0, 'to', 3)) == LogicArray(0b0101, Range(0, 'to', 3))
    assert LogicArray([0, 1, 0, 1], Range(0, 'to', 3)) == LogicArray([0, 1, 0, 1], Range(0, 'to', 3))
    assert LogicArray("0101", Range(0, 'to', 3)) == LogicArray("0101", Range(7, 'downto', 4)) # equality works regardless of range
    assert LogicArray("0101", Range(0, 'to', 3)) != LogicArray("1010", Range(0, 'to', 3))  # wrong value same lengths
    assert LogicArray("0101", Range(0, 'to', 3)) != LogicArray("010101")  # different lengths
    # fmt: on
    assert LogicArray("0101") == "0101"
    assert LogicArray("0101") == [0, 1, 0, 1]
    assert LogicArray("0101") == 0b0101
    assert LogicArray("XXXX") != 1
    assert LogicArray("0101") != object()
    assert LogicArray("0101") != "lol"
    assert LogicArray("0101") != 123
    assert LogicArray("0101") != [7, "f", dict]


def test_repr_eval():
    r = LogicArray("X01Z")
    assert eval(repr(r)) == r


def test_iter():
    val = [Logic(0), Logic(1), Logic("X"), Logic("Z")]
    assert all(isinstance(v, Logic) for v in val)
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
        LogicArray("01XZ")[[]]
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
    a[7:4] = 0b1010
    assert a == LogicArray("1010ZZZZ")


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


def test_null_vector():
    null_range = Range(-1, "downto", 0)
    assert len(null_range) == 0

    # test construction doesn't fail
    LogicArray("")
    LogicArray("", null_range)
    LogicArray([])
    LogicArray([], null_range)
    with pytest.raises(ValueError):
        LogicArray(0, null_range)
    with pytest.raises(ValueError):
        LogicArray.from_unsigned(0, null_range)
    with pytest.raises(ValueError):
        LogicArray.from_signed(0, null_range)

    null_vector = LogicArray("")

    # test attributes
    assert len(null_vector) == 0
    assert list(null_vector) == []
    assert str(null_vector) == ""
    with pytest.raises(ValueError):
        int(null_vector)
    with pytest.raises(ValueError):
        null_vector.to_signed()
    with pytest.raises(ValueError):
        null_vector.to_unsigned()

    # test comparison
    assert null_vector == LogicArray("")
    assert null_vector == LogicArray("", null_range)
    assert null_vector == LogicArray([])
    assert null_vector == LogicArray([], null_range)
    assert null_vector != 0
    assert null_vector != 1
    assert null_vector != -1
    assert null_vector == ""
    assert null_vector == []


def test_bool_cast():
    assert not LogicArray("0000")
    assert LogicArray("0100")
    with pytest.raises(ValueError):
        bool(LogicArray("XZ01"))


def test_resolve():
    assert LogicArray("UX01ZWLH-").resolve("weak") == LogicArray("UX01ZX01-")
    assert LogicArray("UX01ZWLH-").resolve("zeros") == LogicArray("000100010")
    assert LogicArray("UX01ZWLH-").resolve("ones") == LogicArray("110111011")
    assert LogicArray("01LH").resolve("random") == LogicArray("0101")
    array = LogicArray("UXZW-").resolve("random")
    assert all(elem in (Logic("0"), Logic("1")) for elem in array)


def test_copy() -> None:
    l = LogicArray("X01Z", Range(-2, "to", 1))

    with pytest.raises(NotImplementedError):
        copy.copy(l)

    d = copy.deepcopy(l)
    assert l == d
    assert l.range == d.range
