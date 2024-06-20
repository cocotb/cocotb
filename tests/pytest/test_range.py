# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from cocotb.types import Range


def test_to_range():
    r = Range(1, "to", 8)
    assert r.left == 1
    assert r.direction == "to"
    assert r.right == 8
    assert len(r) == 8
    assert list(r) == [1, 2, 3, 4, 5, 6, 7, 8]
    assert list(reversed(r)) == [8, 7, 6, 5, 4, 3, 2, 1]
    assert r[0] == 1
    assert r[7] == 8
    with pytest.raises(IndexError):
        r[8]
    assert r[3:7] == Range(4, "to", 7)
    assert 8 in r
    assert 10 not in r
    assert r.index(7) == 6
    with pytest.raises(ValueError):
        r.index(9)
    assert r.count(4) == 1
    assert r.count(10) == 0


def test_downto_range():
    r = Range(4, "downto", -3)
    assert r.left == 4
    assert r.direction == "downto"
    assert r.right == -3
    assert len(r) == 8
    assert list(r) == [4, 3, 2, 1, 0, -1, -2, -3]
    assert list(reversed(r)) == [-3, -2, -1, 0, 1, 2, 3, 4]
    assert r[0] == 4
    assert r[7] == -3
    with pytest.raises(IndexError):
        r[8]
    assert r[3:7] == Range(1, "downto", -2)
    assert 0 in r
    assert 10 not in r
    assert r.index(2) == 2
    with pytest.raises(ValueError):
        r.index(9)
    assert r.count(4) == 1
    assert r.count(10) == 0


def test_null_range():
    r = Range(1, "downto", 4)
    assert r.left == 1
    assert r.direction == "downto"
    assert r.right == 4
    assert len(r) == 0
    assert list(r) == []
    assert list(reversed(r)) == []
    with pytest.raises(IndexError):
        r[0]
    assert 2 not in r
    with pytest.raises(ValueError):
        r.index(4)
    assert r.count(4) == 0


def test_bad_arguments():
    with pytest.raises(TypeError):
        Range(1, "to")  # nowhere ...
    with pytest.raises(TypeError):
        Range("1", "to", 5)
    with pytest.raises(ValueError):
        Range(1, "BAD DIRECTION", 3)


def test_equality():
    assert Range(7, "downto", -7) == Range(7, "downto", -7)
    assert Range(7, "downto", -7) != Range(0, "to", 8)
    assert Range(1, "to", 0) == Range(8, "to", -8)  # null ranges are all equal?
    assert Range(1, "to", 4) != 789


def test_other_constructors():
    assert Range(1, 8) == Range(1, "to", 8)
    assert Range(3, -4) == Range(3, "downto", -4)
    assert Range(left=1, right=8) == Range(1, "to", 8)
    assert Range(left=3, right=-4) == Range(3, "downto", -4)


def test_use_in_set():
    assert len({Range(1, "to", 8), Range(1, "to", 8)}) == 1
    assert len({Range(1, "to", 8), Range(8, "downto", 1)}) == 2


def test_conversions():
    t = range(10, 1, -1)
    r = Range.from_range(t)
    assert r.left == 10
    assert r.right == 2
    assert r.direction == "downto"
    assert r.to_range() == t


def test_repr():
    r = Range(5, "to", 9)
    assert eval(repr(r)) == r


def test_uppercase_in_direction():
    r = Range(1, "TO", 8)
    assert r.direction == "to"


def test_bad_direction():
    with pytest.raises(ValueError):
        Range(1, "nope", 8)


def test_bad_bound():
    with pytest.raises(TypeError):
        Range(object(), "to", 8)


def test_bad_step():
    with pytest.raises(ValueError):
        Range.from_range(range(10, 5, -2))


def test_bad_getitem():
    with pytest.raises(TypeError):
        Range(10, "downto", 4)["8"]
