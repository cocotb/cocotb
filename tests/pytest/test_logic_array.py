# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from cocotb.binary import BinaryValue
from cocotb.types import Logic, LogicArray, Range, concat


def test_logic_array_constructor():
    LogicArray([False, 1, "X", Logic("Z")])
    l = LogicArray("01XZ")
    assert all(isinstance(v, Logic) for v in l)
    with pytest.raises(ValueError):
        LogicArray([object()])

    assert LogicArray(0) == LogicArray("0")
    assert LogicArray(0xA7) == LogicArray("10100111")
    assert LogicArray(-1) == LogicArray("1")

    assert LogicArray(10, Range(5, "downto", 0)) == LogicArray("001010")
    assert LogicArray(-2, Range(5, "downto", 0)) == LogicArray("111110")
    with pytest.raises(ValueError):
        LogicArray(10, Range(1, "to", 3))

    with pytest.raises(TypeError):
        LogicArray(object())

    with pytest.raises(ValueError):
        LogicArray("101010", Range(0, 'to', 0))


def test_logic_array_properties():
    assert LogicArray(0).integer == 0
    assert LogicArray(0).signed_integer == 0
    assert LogicArray(0).binstr == "0"
    assert LogicArray(10).integer == 10
    assert LogicArray(10).signed_integer == -6
    assert LogicArray(10).binstr == "1010"
    assert LogicArray(-6).integer == 10
    assert LogicArray(-6).signed_integer == -6
    assert LogicArray(-6).binstr == "1010"
    assert LogicArray(0).is_resolvable
    assert not LogicArray("1X1").is_resolvable


def test_logic_array_setattr():
    l = LogicArray("0000")
    l[1] = "X"
    assert l == LogicArray("00X0")
    with pytest.raises(TypeError):
        l[object()] = "X"


def test_logic_array_repr():
    l = LogicArray("1XX110")
    assert eval(repr(l)) == l


def test_logic_array_concat():
    l = LogicArray("01ZX", Range(0, "to", 3))
    p = LogicArray("1101")
    assert concat(l, p) == LogicArray("01ZX1101")
    with pytest.raises(TypeError):
        concat(l, "nope")


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


def test_binaryvalue_conversion():
    b = BinaryValue(3, n_bits=5)
    assert LogicArray(b) == LogicArray("11000")
