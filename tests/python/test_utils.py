import pytest

from cocotb.utils import int_to_bytes, int_from_bytes

@pytest.mark.parametrize('val, length, byteorder, bytes', [
    (         0, 2,    'big',         b'\x00\x00'),  # noqa E201
    (         0, 2, 'little',         b'\x00\x00'),  # noqa E201
    (      0x55, 2, 'little',         b'\x55\x00'),  # noqa E201
    (      0x55, 2,    'big',         b'\x00\x55'),  # noqa E201
    (      0x55, 4, 'little', b'\x55\x00\x00\x00'),  # noqa E201
    (      0x55, 4,    'big', b'\x00\x00\x00\x55'),  # noqa E201
    (0x80000000, 4,    'big', b'\x80\x00\x00\x00'),  # noqa E201
    (0x80000000, 4, 'little', b'\x00\x00\x00\x80'),  # noqa E201
])
def test_int_to_bytes(val, length, byteorder, bytes):
    assert int_to_bytes(val, length, byteorder) == bytes


@pytest.mark.parametrize('bytes, byteorder, signed, val', [
    (        b'\x80',    'big',  True,      -128),  # noqa E201
    (        b'\x80',    'big', False,       128),  # noqa E201
    (        b'\x7F',    'big',  True,       127),  # noqa E201
    (    b'\x00\x00',    'big',  True,         0),  # noqa E201
    (    b'\x00\x00',    'big', False,         0),  # noqa E201
    (    b'\x00\x00', 'little', False,         0),  # noqa E201
    (    b'\x00\x01',    'big', False,    0x0001),  # noqa E201
    (    b'\x00\x01', 'little', False,    0x0100),  # noqa E201
    (    b'\x80\x00',    'big', False,    0x8000),  # noqa E201
    (    b'\x80\x00',    'big',  True,   -0x8000),  # noqa E201
    (    b'\xFF\xFF',    'big',  True,   -0x0001),  # noqa E201
    (    b'\x7F\xFF',    'big',  True,    0x7FFF),  # noqa E201
    (b'\xFF\xFF\xFF',    'big',  True, -0x000001),  # noqa E201
    (b'\x7F\xFF\xFF',    'big',  True,  0x7FFFFF),  # noqa E201
    (b'\xFF\xFF\xFF',    'big', False,  0xFFFFFF),  # noqa E201
])
def test_int_from_bytes(bytes, byteorder, signed, val):
    assert int_from_bytes(bytes, byteorder, signed=signed) == val
