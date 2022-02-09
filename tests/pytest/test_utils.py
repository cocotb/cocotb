# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import ctypes

import pytest

import cocotb.utils


class TestHexDump:
    def test_int_illegal(dut):
        # this used to be legal, but deliberately is no longer
        with pytest.raises(TypeError):
            cocotb.utils.hexdump(1)

    def test_str_deprecated(dut):
        with pytest.warns(DeprecationWarning) as w:
            dump_str = cocotb.utils.hexdump("\x20\x65\x00\xff")
        assert "str" in str(w[-1].message)
        assert "bytes instead" in str(w[-1].message)

        dump_bytes = cocotb.utils.hexdump(b"\x20\x65\x00\xff")
        assert dump_bytes == dump_str


class TestHexDiffs:
    def test_int_illegal(dut):
        # this used to be legal, but deliberately is no longer
        with pytest.raises(TypeError):
            cocotb.utils.hexdiffs(0, 1)

    def test_str_deprecated(dut):
        with pytest.warns(DeprecationWarning) as w:
            diff_str = cocotb.utils.hexdiffs("\x20\x65\x00\xff", "\x20\x00\x65")
        assert "str" in str(w[-1].message)
        assert "bytes instead" in str(w[-1].message)

        diff_bytes = cocotb.utils.hexdiffs(b"\x20\x65\x00\xff", b"\x20\x00\x65")
        assert diff_bytes == diff_str


def test_pack_deprecated():
    class Example(ctypes.Structure):
        _fields_ = [("a", ctypes.c_byte), ("b", ctypes.c_byte)]

    e = Example(a=0xCC, b=0x55)

    with pytest.warns(DeprecationWarning):
        a = cocotb.utils.pack(e)

    assert a == bytes(e)


def test_unpack_deprecated():
    class Example(ctypes.Structure):
        _fields_ = [("a", ctypes.c_byte), ("b", ctypes.c_byte)]

    e = Example(a=0xCC, b=0x55)
    f = Example(a=0xCC, b=0x55)

    b = b"\x01\x02"

    with pytest.warns(DeprecationWarning):
        cocotb.utils.unpack(e, b)

    assert e.a == 1 and e.b == 2

    memoryview(f).cast("B")[:] = b

    assert f.a == 1 and f.b == 2
