# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import pytest
from cocotb.types import Logic


def test_logic_conversions():
    l = Logic("U")
    assert Logic("u") == l
    assert Logic(Logic("U")) == l

    l = Logic("X")
    assert Logic("x") == l
    assert Logic(Logic("x")) == l

    l = Logic("0")
    assert Logic(0) == l
    assert Logic(False) == l
    assert Logic(Logic("0")) == l

    l = Logic("1")
    assert Logic(1) == l
    assert Logic(True) == l
    assert Logic(Logic("1")) == l

    l = Logic("Z")
    assert Logic("z") == l
    assert Logic(Logic("Z")) == l

    l = Logic("W")
    assert Logic("w") == l
    assert Logic(Logic("W")) == l

    l = Logic("L")
    assert Logic("l") == l
    assert Logic(Logic("L")) == l

    l = Logic("H")
    assert Logic("h") == l
    assert Logic(Logic("H")) == l

    l = Logic("-")
    assert Logic(Logic("-")) == l

    for value in ("j", 2, object()):
        with pytest.raises(ValueError):
            Logic(value)


def test_logic_equality():
    assert Logic(0) == Logic("0")
    assert Logic(0) != Logic("X")
    assert Logic(0) != object()
    assert Logic(0) == 0
    assert Logic("X") == "X"
    assert Logic("X") != "j"
    assert Logic("1") != 5


def test_logic_default_value():
    assert Logic() == Logic("X")


def test_logic_bool_conversions():
    assert bool(Logic("1")) is True
    assert bool(Logic("0")) is False
    with pytest.raises(ValueError):
        bool(Logic("X"))
    with pytest.raises(ValueError):
        bool(Logic("Z"))


def test_logic_str_conversions():
    assert str(Logic("0")) == "0"
    assert str(Logic("1")) == "1"
    assert str(Logic("X")) == "X"
    assert str(Logic("Z")) == "Z"


def test_logic_int_conversions():
    assert int(Logic("0")) == 0
    assert int(Logic("1")) == 1
    with pytest.raises(ValueError):
        int(Logic("X"))
    with pytest.raises(ValueError):
        int(Logic("Z"))


def test_logic_repr():
    assert eval(repr(Logic("0"))) == Logic("0")
    assert eval(repr(Logic("1"))) == Logic("1")
    assert eval(repr(Logic("X"))) == Logic("X")
    assert eval(repr(Logic("Z"))) == Logic("Z")


def test_logic_and():
    # will not be exhaustive
    assert Logic("0") & Logic("Z") == Logic(0)
    assert Logic(1) & Logic("1") == Logic(1)
    assert Logic("X") & Logic("Z") == Logic("X")
    with pytest.raises(TypeError):
        Logic("1") & 8
    with pytest.raises(TypeError):
        8 & Logic("1")


def test_logic_or():
    # will not be exhaustive
    assert Logic("1") | Logic("Z") == Logic("1")
    assert Logic(0) | Logic("0") == Logic(0)
    assert Logic("X") | Logic("Z") == Logic("X")
    with pytest.raises(TypeError):
        8 | Logic(0)
    with pytest.raises(TypeError):
        Logic(0) | 8


def test_logic_xor():
    # will not be exhaustive
    assert (Logic("1") ^ Logic(True)) == Logic(0)
    assert (Logic(1) ^ Logic("X")) == Logic("X")
    assert (Logic(1) ^ Logic(False)) == Logic(1)
    with pytest.raises(TypeError):
        Logic(1) ^ ()
    with pytest.raises(TypeError):
        () ^ Logic(1)


def test_logic_invert():
    assert ~Logic(0) == Logic(1)
    assert ~Logic(1) == Logic(0)
    assert ~Logic("X") == Logic("X")
    assert ~Logic("Z") == Logic("X")


def test_logic_identity():
    assert Logic(0) is Logic(False)
    assert Logic("1") is Logic(1)
    assert Logic("X") is Logic("x")
    assert Logic("z") is Logic("Z")
