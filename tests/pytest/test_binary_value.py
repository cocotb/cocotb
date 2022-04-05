# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from cocotb.binary import BinaryRepresentation, BinaryValue

TRUNCATION_MATCH = r"\d+-bit value requested, truncating value"


def test_init_zero_length():
    bin1 = BinaryValue(
        value=0, n_bits=0, binaryRepresentation=BinaryRepresentation.UNSIGNED
    )
    assert bin1._str == ""
    assert bin1.binstr == ""
    assert bin1.integer == 0

    bin2 = BinaryValue(
        value=0, n_bits=0, binaryRepresentation=BinaryRepresentation.TWOS_COMPLEMENT
    )
    assert bin2._str == ""
    assert bin2.binstr == ""
    assert bin2.integer == 0

    bin3 = BinaryValue(
        value=0, n_bits=0, binaryRepresentation=BinaryRepresentation.SIGNED_MAGNITUDE
    )
    assert bin3._str == ""
    assert bin3.binstr == ""
    assert bin3.integer == 0

    # Whatever value is set to a zero bit long BinaryValue, it should read 0
    with pytest.warns(RuntimeWarning, match=TRUNCATION_MATCH):
        bin4 = BinaryValue(
            value=10,
            n_bits=0,
            binaryRepresentation=BinaryRepresentation.SIGNED_MAGNITUDE,
        )
    assert bin4._str == ""
    assert bin4.binstr == ""
    assert bin4.integer == 0

    with pytest.warns(RuntimeWarning, match=TRUNCATION_MATCH):
        bin4.value = 5
    assert bin4._str == ""
    assert bin4.binstr == ""
    assert bin4.integer == 0


def test_init_big_endian_twos_comp():
    bin1 = BinaryValue(
        value=-1,
        n_bits=2,
        bigEndian=True,
        binaryRepresentation=BinaryRepresentation.TWOS_COMPLEMENT,
    )
    assert bin1._str == "11"
    assert bin1.binstr == "11"
    assert bin1.integer == -1


def test_init_little_endian_unsigned():
    bin1 = BinaryValue(
        value=3,
        n_bits=3,
        bigEndian=False,
        binaryRepresentation=BinaryRepresentation.UNSIGNED,
    )
    assert bin1._str == "011"
    assert bin1.binstr == "011"
    assert bin1.integer == 3

    bin2 = BinaryValue(
        value=5,
        n_bits=5,
        bigEndian=False,
        binaryRepresentation=BinaryRepresentation.UNSIGNED,
    )
    assert bin2._str == "00101"
    assert bin2.binstr == "00101"
    assert bin2.integer == 5

    bin3 = BinaryValue(
        value=12,
        n_bits=8,
        bigEndian=False,
        binaryRepresentation=BinaryRepresentation.UNSIGNED,
    )
    assert bin3._str == "00001100"
    assert bin3.binstr == "00001100"
    assert bin3.integer == 12

    bin4 = BinaryValue(
        value="010110",
        bigEndian=False,
        binaryRepresentation=BinaryRepresentation.UNSIGNED,
    )
    assert bin4._str == "010110"
    assert bin4.binstr == "010110"
    assert bin4.integer == 22

    bin5 = BinaryValue(
        value="1001011",
        bigEndian=False,
        binaryRepresentation=BinaryRepresentation.UNSIGNED,
    )
    assert bin5._str == "1001011"
    assert bin5.binstr == "1001011"
    assert bin5.integer == 75

    bin6 = BinaryValue(
        value="11111111111111111111110000101100",
        n_bits=32,
        bigEndian=False,
        binaryRepresentation=BinaryRepresentation.UNSIGNED,
    )
    assert bin6._str == "11111111111111111111110000101100"
    assert bin6.binstr == "11111111111111111111110000101100"
    assert bin6.signed_integer == -980
    assert bin6.integer == 4294966316


def test_init_little_endian_signed():
    bin1 = BinaryValue(
        value=3,
        n_bits=3,
        bigEndian=False,
        binaryRepresentation=BinaryRepresentation.SIGNED_MAGNITUDE,
    )
    assert bin1._str == "011"
    assert bin1.binstr == "011"
    assert bin1.integer == 3

    bin2 = BinaryValue(
        value=-1,
        n_bits=2,
        bigEndian=False,
        binaryRepresentation=BinaryRepresentation.SIGNED_MAGNITUDE,
    )
    assert bin2._str == "11"
    assert bin2.binstr == "11"
    assert bin2.integer == -1

    bin3 = BinaryValue(
        value="1001011",
        bigEndian=False,
        binaryRepresentation=BinaryRepresentation.SIGNED_MAGNITUDE,
    )
    assert bin3._str == "1001011"
    assert bin3.binstr == "1001011"
    assert bin3.integer == -11


def test_init_little_endian_twos_comp():
    bin1 = BinaryValue(
        value=3,
        n_bits=4,
        bigEndian=False,
        binaryRepresentation=BinaryRepresentation.TWOS_COMPLEMENT,
    )
    assert bin1._str == "0011"
    assert bin1.binstr == "0011"
    assert bin1.integer == 3

    bin2 = BinaryValue(
        value=-1,
        n_bits=2,
        bigEndian=False,
        binaryRepresentation=BinaryRepresentation.TWOS_COMPLEMENT,
    )
    assert bin2._str == "11"
    assert bin2.binstr == "11"
    assert bin2.integer == -1

    bin3 = BinaryValue(
        value=-65,
        n_bits=8,
        bigEndian=False,
        binaryRepresentation=BinaryRepresentation.TWOS_COMPLEMENT,
    )
    assert bin3._str == "10111111"
    assert bin3.binstr == "10111111"
    assert bin3.integer == -65

    bin4 = BinaryValue(
        value=1,
        n_bits=2,
        bigEndian=False,
        binaryRepresentation=BinaryRepresentation.TWOS_COMPLEMENT,
    )
    assert bin4._str == "01"
    assert bin4.binstr == "01"
    assert bin4.integer == 1

    bin5 = BinaryValue(
        value="1001011",
        bigEndian=False,
        binaryRepresentation=BinaryRepresentation.TWOS_COMPLEMENT,
    )
    assert bin5._str == "1001011"
    assert bin5.binstr == "1001011"
    assert bin5.integer == -53

    temp_bin = BinaryValue(
        value="11111111111111111111110000101100",
        bigEndian=False,
        binaryRepresentation=BinaryRepresentation.UNSIGNED,
    )

    # Illegal to construct from another BinaryValue (used to silently fail)
    with pytest.raises(TypeError):
        BinaryValue(
            value=temp_bin,
            n_bits=32,
            binaryRepresentation=BinaryRepresentation.TWOS_COMPLEMENT,
        )

    bin7 = BinaryValue(
        value=temp_bin.binstr,
        n_bits=32,
        bigEndian=False,
        binaryRepresentation=BinaryRepresentation.TWOS_COMPLEMENT,
    )
    assert bin7._str == "11111111111111111111110000101100"
    assert bin7.binstr == "11111111111111111111110000101100"
    assert bin7.get_value_signed() == -980
    assert bin7.integer == -980


def test_init_unsigned_negative_value():
    with pytest.raises(ValueError):
        BinaryValue(
            value=-8,
            n_bits=5,
            bigEndian=True,
            binaryRepresentation=BinaryRepresentation.UNSIGNED,
        )
        pytest.fail(
            "Expected ValueError when assigning negative number to unsigned BinaryValue"
        )


def test_init_not_enough_bits():
    with pytest.warns(RuntimeWarning, match=TRUNCATION_MATCH):
        bin1_unsigned = BinaryValue(
            value=128,
            n_bits=7,
            bigEndian=True,
            binaryRepresentation=BinaryRepresentation.UNSIGNED,
        )
    assert bin1_unsigned._str == "0000000"
    assert bin1_unsigned.binstr == "0000000"
    assert bin1_unsigned.integer == 0

    with pytest.warns(RuntimeWarning, match=TRUNCATION_MATCH):
        bin1_sigmag = BinaryValue(
            value=128,
            n_bits=7,
            bigEndian=True,
            binaryRepresentation=BinaryRepresentation.SIGNED_MAGNITUDE,
        )
    assert bin1_sigmag._str == "0000000"
    assert bin1_sigmag.binstr == "0000000"
    assert bin1_sigmag.integer == 0

    with pytest.warns(RuntimeWarning, match=TRUNCATION_MATCH):
        bin1_twoscomp = BinaryValue(
            value=128,
            n_bits=7,
            bigEndian=True,
            binaryRepresentation=BinaryRepresentation.TWOS_COMPLEMENT,
        )
    assert bin1_twoscomp._str == "0000000"
    assert bin1_twoscomp.binstr == "0000000"
    assert bin1_twoscomp.integer == 0

    with pytest.warns(RuntimeWarning, match=TRUNCATION_MATCH):
        bin1_binstr = BinaryValue(value="110000000", n_bits=7, bigEndian=True)
    assert bin1_binstr._str == "0000000"
    assert bin1_binstr.binstr == "0000000"
    assert bin1_binstr.integer == 0

    with pytest.warns(RuntimeWarning, match=TRUNCATION_MATCH):
        bin2 = BinaryValue(
            value="1111110000101100",
            n_bits=12,
            bigEndian=False,
            binaryRepresentation=BinaryRepresentation.TWOS_COMPLEMENT,
        )
    assert bin2._str == "110000101100"
    assert bin2.binstr == "110000101100"
    assert bin2.integer == -980

    with pytest.warns(RuntimeWarning, match=TRUNCATION_MATCH):
        bin3 = BinaryValue(
            value="1111110000101100",
            n_bits=11,
            bigEndian=False,
            binaryRepresentation=BinaryRepresentation.SIGNED_MAGNITUDE,
        )
    assert bin3._str == "10000101100"
    assert bin3.binstr == "10000101100"
    assert bin3.integer == -44


def test_init_short_binstr_value():
    bin1 = BinaryValue(
        value="0",
        n_bits=4,
        bigEndian=True,
        binaryRepresentation=BinaryRepresentation.UNSIGNED,
    )
    assert bin1._str == "0000"
    assert bin1.binstr == "0000"
    assert bin1.integer == 0

    bin2 = BinaryValue(
        value="Z",
        n_bits=8,
        bigEndian=False,
        binaryRepresentation=BinaryRepresentation.UNSIGNED,
    )
    assert bin2._str == "0000000Z"
    assert bin2.binstr == "0000000Z"
    with pytest.raises(ValueError):
        bin2.integer
        pytest.fail("Expected ValueError when resolving Z to integer")

    bin3 = BinaryValue(
        value="01",
        n_bits=8,
        bigEndian=False,
        binaryRepresentation=BinaryRepresentation.SIGNED_MAGNITUDE,
    )
    assert bin3._str == "00000001"
    assert bin3.binstr == "00000001"
    assert bin3.integer == 1

    bin4 = BinaryValue(
        value="1",
        n_bits=8,
        bigEndian=True,
        binaryRepresentation=BinaryRepresentation.SIGNED_MAGNITUDE,
    )
    # 1 digit is too small for Signed Magnitude representation, so setting binstr will fail, falling back to buff
    bin4._str == "10000000"
    bin4.binstr == "10000000"
    bin4.integer == 1


def test_defaults():
    bin1 = BinaryValue(17)
    assert bin1.binaryRepresentation == BinaryRepresentation.UNSIGNED
    assert bin1.big_endian is True
    assert bin1._n_bits is None
    assert bin1.integer == 17


def test_index():
    bin1 = BinaryValue(
        value=-980,
        n_bits=32,
        bigEndian=False,
        binaryRepresentation=BinaryRepresentation.TWOS_COMPLEMENT,
    )

    bin2 = bin1[3:2]
    assert bin2.binstr == "11"
    assert bin2.integer == -1

    with pytest.raises(IndexError):
        bin1[32]

    with pytest.raises(IndexError):
        bin1[1:2]

    with pytest.raises(IndexError):
        bin1[-1:4]

    with pytest.raises(IndexError):
        bin1[2:-2]

    bin3 = BinaryValue(
        value=154,
        n_bits=14,
        bigEndian=True,
        binaryRepresentation=BinaryRepresentation.UNSIGNED,
    )

    with pytest.raises(IndexError):
        bin3[14]

    with pytest.raises(IndexError):
        bin3[2:1]

    with pytest.raises(IndexError):
        bin3[-1:4]

    with pytest.raises(IndexError):
        bin3[2:-2]


def test_general():
    """
    Test out the cocotb supplied BinaryValue class for manipulating
    values in a style familiar to rtl coders.
    """

    vec = BinaryValue(value=0, n_bits=16)
    assert vec.n_bits == 16
    assert vec.big_endian is True
    assert vec.integer == 0

    # Checking single index assignment works as expected on a Little Endian BinaryValue
    vec = BinaryValue(value=0, n_bits=16, bigEndian=False)
    assert vec.big_endian is False
    for idx in range(vec.n_bits):
        vec[idx] = "1"
        expected_value = 2 ** (idx + 1) - 1
        assert vec.integer == expected_value
        assert vec[idx] == 1

    # Checking slice assignment works as expected on a Little Endian BinaryValue
    assert vec.integer == 65535
    vec[7:0] = "00110101"
    assert vec.binstr == "1111111100110101"
    assert vec[7:0].binstr == "00110101"


def test_backwards_compatibility():
    """
    Test backwards-compatibility wrappers for BinaryValue
    """

    # bits is deprecated in favor of n_bits
    with pytest.deprecated_call():
        vec = BinaryValue(value=0, bits=16)
    assert vec.n_bits == 16

    vec = BinaryValue(0, 16)
    assert vec.n_bits == 16

    with pytest.raises(TypeError):
        BinaryValue(value=0, bits=16, n_bits=17)


def test_buff_big_endian():
    orig_str = "0110" + "1100" + "1001"
    orig_bytes = b"\x06\xC9"  # padding is the high bits of the first byte

    v = BinaryValue(value=orig_str, n_bits=12, bigEndian=True)
    assert v.buff == orig_bytes

    with pytest.warns(RuntimeWarning, match=TRUNCATION_MATCH):
        # the binstr is truncated, but its value should be unchanged
        v.buff = orig_bytes
    assert v.buff == orig_bytes
    assert v.binstr == orig_str

    with pytest.warns(RuntimeWarning, match=TRUNCATION_MATCH):
        # extra bits are stripped because they don't fit into the 12 bits
        v.buff = b"\xF6\xC9"
    assert v.buff == orig_bytes
    assert v.binstr == orig_str


def test_buff_little_endian():
    orig_str = "0110" + "1100" + "1001"
    orig_bytes = b"\xC9\x06"  # padding is the high bits of the last byte

    v = BinaryValue(value=orig_str, n_bits=12, bigEndian=False)
    assert v.buff == orig_bytes

    with pytest.warns(RuntimeWarning, match=TRUNCATION_MATCH):
        # the binstr is truncated, but its value should be unchanged
        v.buff = orig_bytes
    assert v.buff == orig_bytes
    assert v.binstr == orig_str

    with pytest.warns(RuntimeWarning, match=TRUNCATION_MATCH):
        # extra bits are stripped because they don't fit into the 12 bits
        v.buff = b"\xC9\xF6"
    assert v.buff == orig_bytes
    assert v.binstr == orig_str


def test_bad_binstr():
    with pytest.raises(
        ValueError, match=r"Attempting to assign character 4 to a BinaryValue"
    ):
        BinaryValue(value="01XZ4")

    with pytest.raises(
        ValueError, match=r"Attempting to assign character % to a BinaryValue"
    ):
        BinaryValue(value="Uu%")
