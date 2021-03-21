# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from cocotb.types import Logic, Bit
import pytest


def test_logic_conversions():
    Logic(0)
    Logic(1)
    Logic(True)
    Logic(False)
    Logic('0')
    Logic('l')
    Logic('L')
    Logic('1')
    Logic('h')
    Logic('H')
    Logic('x')
    Logic('X')
    Logic('w')
    Logic('W')
    Logic('u')
    Logic('U')
    Logic('z')
    Logic('Z')
    Logic(Logic('0'))
    Logic(Logic('1'))
    Logic(Logic('X'))
    Logic(Logic('Z'))
    with pytest.raises(ValueError):
        Logic('j')


def test_bit_conversions():
    Bit(0)
    Bit(1)
    Bit(False)
    Bit(True)
    Bit('0')
    Bit('1')
    Bit(Bit('0'))
    Bit(Bit('1'))
    with pytest.raises(ValueError):
        _ = Bit(object())


def test_bit_logic_conversions():
    Logic(Bit(0))
    Logic(Bit(1))
    Bit(Logic(0))
    Bit(Logic(1))
    with pytest.raises(ValueError):
        Bit(Logic('X'))
    with pytest.raises(ValueError):
        Bit(Logic('Z'))


def test_logic_equality():
    assert Logic(0) == Logic('0')
    assert Logic(0) != Logic('X')
    assert Logic(0) != object()


def test_bit_equality():
    assert Bit(0) == Bit(False)
    assert Bit(1) != Bit('0')
    assert Bit(1) != object()


def test_logic_bit_equality():
    assert Logic(0) != Bit(0)


def test_logic_default_value():
    assert Logic() == Logic('X')


def test_bit_default_value():
    assert Bit() == Bit('0')


def test_logic_bool_conversions():
    assert bool(Logic('1')) is True
    assert bool(Logic('0')) is False
    with pytest.raises(ValueError):
        bool(Logic('X'))
    with pytest.raises(ValueError):
        bool(Logic('Z'))


def test_bit_bool_conversions():
    assert bool(Bit(1)) is True
    assert bool(Bit(0)) is False


def test_logic_str_conversions():
    assert str(Logic('0')) == '0'
    assert str(Logic('1')) == '1'
    assert str(Logic('X')) == 'X'
    assert str(Logic('Z')) == 'Z'


def test_bit_str_conversions():
    assert str(Bit(0)) == '0'
    assert str(Bit(1)) == '1'


def test_logic_int_conversions():
    assert int(Logic('0')) == 0
    assert int(Logic('1')) == 1
    with pytest.raises(ValueError):
        int(Logic('X'))
    with pytest.raises(ValueError):
        int(Logic('Z'))


def test_bit_int_conversions():
    assert int(Bit('0')) == 0
    assert int(Bit('1')) == 1


def test_logic_repr():
    assert eval(repr(Logic('0'))) == Logic('0')
    assert eval(repr(Logic('1'))) == Logic('1')
    assert eval(repr(Logic('X'))) == Logic('X')
    assert eval(repr(Logic('Z'))) == Logic('Z')


def test_bit_repr():
    assert eval(repr(Bit('0'))) == Bit('0')
    assert eval(repr(Bit('1'))) == Bit('1')


def test_logic_and():
    # will not be exhaustive
    assert Logic('0') & Logic('Z') == Logic(0)
    assert Logic(1) & Logic('1') == Logic(1)
    assert Logic('X') & Logic('Z') == Logic('X')
    with pytest.raises(TypeError):
        Logic('1') & 8
    with pytest.raises(TypeError):
        8 & Logic('1')


def test_bit_and():
    assert Bit('0') & Bit('1') == Bit(0)
    assert Bit(1) & Bit('1') == Bit(1)
    with pytest.raises(TypeError):
        Bit('1') & 8
    with pytest.raises(TypeError):
        8 & Bit('1')


def test_logic_bit_and():
    r = Logic(0) & Bit(1)
    assert type(r) == Logic
    assert r == Logic(0)
    r = Bit(1) & Logic(0)
    assert type(r) == Logic
    assert r == Logic(0)


def test_logic_or():
    # will not be exhaustive
    assert Logic('1') | Logic('Z') == Logic('1')
    assert Logic(0) | Logic('0') == Logic(0)
    assert Logic('X') | Logic('Z') == Logic('X')
    with pytest.raises(TypeError):
        8 | Logic(0)
    with pytest.raises(TypeError):
        Logic(0) | 8


def test_bit_or():
    assert Bit('0') | Bit('1') == Bit(1)
    assert Bit(0) | Bit(False) == Bit(0)
    with pytest.raises(TypeError):
        8 | Bit(0)
    with pytest.raises(TypeError):
        Bit(0) | 8


def test_logic_bit_or():
    r = Logic(0) | Bit(1)
    assert type(r) == Logic
    assert r == Logic(1)
    r = Bit(1) | Logic(0)
    assert type(r) == Logic
    assert r == Logic(1)


def test_logic_xor():
    # will not be exhaustive
    assert (Logic('1') ^ Logic(True)) == Logic(0)
    assert (Logic(1) ^ Logic('X')) == Logic('X')
    assert (Logic(1) ^ Logic(False)) == Logic(1)
    with pytest.raises(TypeError):
        Logic(1) ^ ()
    with pytest.raises(TypeError):
        () ^ Logic(1)


def test_bit_xor():
    assert Bit(0) ^ Bit('1') == Bit(1)
    assert Bit(False) ^ Bit(0) == Bit('0')
    with pytest.raises(TypeError):
        Bit(1) ^ ()
    with pytest.raises(TypeError):
        () ^ Bit(1)


def test_logic_bit_xor():
    r = Logic(0) ^ Bit(1)
    assert type(r) == Logic
    assert r == Logic(1)
    r = Bit(0) ^ Logic(0)
    assert type(r) == Logic
    assert r == Logic(0)


def test_logic_invert():
    assert ~Logic(0) == Logic(1)
    assert ~Logic(1) == Logic(0)
    assert ~Logic('X') == Logic('X')
    assert ~Logic('Z') == Logic('X')


def test_bit_invert():
    assert ~Bit(0) == Bit(1)
    assert ~Bit(1) == Bit(0)
