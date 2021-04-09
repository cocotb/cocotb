# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from cocotb.types import Array, BitArray, Logic, LogicArray, Range, concat


def test_logic_array_constructor():
    LogicArray([False, 1, "X", Logic("Z")])
    l = LogicArray("01XZ")
    assert all(isinstance(v, Logic) for v in l)
    with pytest.raises(ValueError):
        LogicArray([object()])


def test_logic_array_setattr():
    l = LogicArray("0000")
    l[2] = "X"
    assert l == LogicArray("00X0")
    with pytest.raises(TypeError):
        l[object()] = "X"


def test_logic_array_str():
    s = "01ZX"
    l = LogicArray(s)
    assert str(l) == s


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


def test_logic_array_concat_promotion():
    assert type(concat(LogicArray(""), LogicArray(""))) is LogicArray
    assert type(concat(LogicArray(""), BitArray(""))) is LogicArray
    assert type(concat(LogicArray(""), Array(""))) is Array
    assert type(concat(BitArray(""), LogicArray(""))) is LogicArray
    assert type(concat(BitArray(""), BitArray(""))) is BitArray
    assert type(concat(BitArray(""), Array(""))) is Array
    assert type(concat(Array(""), LogicArray(""))) is Array
    assert type(concat(Array(""), BitArray(""))) is Array
    assert type(concat(Array(""), Array(""))) is Array


def test_logic_array_bitwise_promption():
    assert type(LogicArray("") & LogicArray("")) is LogicArray
    assert type(LogicArray("") & BitArray("")) is LogicArray
    assert type(BitArray("") & LogicArray("")) is LogicArray
    assert type(BitArray("") & BitArray("")) is BitArray
