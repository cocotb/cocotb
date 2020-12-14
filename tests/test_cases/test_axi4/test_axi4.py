#!/usr/bin/env python
# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test to demonstrate functionality of the AXI4 master interface"""

from random import randint, randrange, getrandbits

import cocotb
from cocotb.clock import Clock
from cocotb.regression import TestFactory
from cocotb.result import TestFailure
from cocotb.triggers import ClockCycles, Combine, Join, RisingEdge

from cocotb_bus.drivers.amba import (
    AXIBurst, AXI4LiteMaster, AXI4Master, AXIProtocolError, AXIReadBurstLengthMismatch,
    AXIxRESP
)


CLK_PERIOD = (10, "ns")
AXI_PREFIX = "S_AXI"


def get_parameters(dut):
    address_width = dut.ADDR_WIDTH.value // 8
    data_width = dut.DATA_WIDTH.value // 8
    ram_start = dut.RAM_BASE_ADDRESS.value
    ram_stop = ram_start + 2**dut.RAM_WIDTH.value
    return address_width, data_width, ram_start, ram_stop


def add_wstrb_mask(data_width, previous_value, write_value, wstrb):
    result = 0
    for i in range(data_width):
        source = write_value if wstrb & (1 << i) else previous_value
        result |= (source & (0xff << (i * 8)))

    return result


def compare_read_values(expected_values, read_values, burst, burst_length,
                        address):
    for i, (expected, read) in enumerate(zip(expected_values, read_values)):
        if expected != read:
            raise TestFailure(
                "Read {:#x} at beat {}/{} of {} burst with starting address "
                "{:#x}, but was expecting {:#x})"
                .format(read.integer, i + 1, burst_length, burst.name, address,
                        expected))


async def setup_dut(dut):
    cocotb.fork(Clock(dut.clk, *CLK_PERIOD).start())
    dut.rstn <= 0
    await ClockCycles(dut.clk, 2)
    dut.rstn <= 1
    await ClockCycles(dut.clk, 2)


async def test_single_beat(dut, driver, address_latency, data_latency):
    """Test single read/write"""

    axim = driver(dut, AXI_PREFIX, dut.clk)
    _, data_width, ram_start, ram_stop = get_parameters(dut)

    await setup_dut(dut)

    address = randrange(ram_start, ram_stop, data_width)
    write_value = randrange(0, 2**(data_width * 8))
    strobe = randrange(1, 2**data_width)

    previous_value = await axim.read(address)
    await axim.write(address, write_value, byte_enable=strobe,
                     address_latency=address_latency,
                     data_latency=data_latency)
    read_value = await axim.read(address)

    if isinstance(read_value, list):
        previous_value = previous_value[0]
        read_value = read_value[0]

    expected_value = add_wstrb_mask(data_width, previous_value.integer,
                                    write_value, strobe)

    if read_value != expected_value:
        raise TestFailure("Read {:#x} from {:#x} but was expecting {:#x} "
                          "({:#x} with {:#x} as strobe and {:#x} as previous "
                          "value)"
                          .format(read_value.integer, address, expected_value,
                                  write_value, strobe, previous_value))


async def test_incr_burst(dut, size, return_rresp):
    """Test burst reads/writes"""

    axim = AXI4Master(dut, AXI_PREFIX, dut.clk)
    _, data_width, ram_start, ram_stop = get_parameters(dut)
    size = size if size else data_width

    await setup_dut(dut)

    burst_length = randrange(2, 256)
    base = randrange(ram_start, ram_stop, 4096)
    offset = randrange(0, 4096 - (burst_length - 1) * size, size)
    address = base + offset
    write_values = [randrange(0, 2**(size * 8)) for i in range(burst_length)]

    # Make strobe one item less than data, to test also that driver behavior
    strobes = [randrange(0, 2**size) for i in range(len(write_values) - 1)]

    previous_values = await axim.read(address, len(write_values), size=size)
    await axim.write(address, write_values, byte_enable=strobes, size=size)
    read_values = await axim.read(address, len(write_values),
                                  return_rresp=return_rresp, size=size)

    if return_rresp:
        read_values, rresp_list = zip(*read_values)
        for i, rresp in enumerate(rresp_list):
            if rresp is not AXIxRESP.OKAY:
                raise TestFailure(
                    "Read at beat {}/{} with starting address {:#x} failed "
                    "with RRESP {} ({})"
                    .format(i + 1, len(rresp_list), address, rresp.value,
                            rresp.name))

    strobes += [strobes[-1]]
    expected_values = \
        [add_wstrb_mask(size, previous_value, write_value, wstrb)
         for previous_value, write_value, wstrb
         in zip(previous_values, write_values, strobes)]

    for i in range(len(read_values)):
        if expected_values[i] != read_values[i]:
            raise TestFailure(
                "Read {:#x} at beat {}/{} with starting address {:#x}, but "
                "was expecting {:#x} ({:#x} with {:#x} as strobe and {:#x} as "
                "previous value)"
                .format(read_values[i].integer, i + 1, burst_length, address,
                        expected_values[i], write_values[i], strobes[i],
                        previous_values[i].integer))


async def test_fixed_wrap_burst(dut, size, burst_length=16):
    """Test FIXED and WRAP read/writes"""

    axim = AXI4Master(dut, AXI_PREFIX, dut.clk)
    _, data_width, ram_start, ram_stop = get_parameters(dut)
    size = size if size else data_width

    await setup_dut(dut)

    base = randrange(ram_start, ram_stop, 4096)
    offset = randrange(0, 4096 - (burst_length - 1) * size, size)
    address = base + offset

    for burst in (AXIBurst.FIXED, AXIBurst.WRAP):

        write_values = \
            [randrange(0, 2**(size * 8)) for i in range(burst_length)]

        await axim.write(address, write_values, burst=burst, size=size)

        if burst is AXIBurst.FIXED:
            # A FIXED write on a memory is like writing the last element,
            # reading it with a FIXED burst returns always the same value.
            expected_values = [write_values[-1]] * burst_length
        else:
            # Regardless of the boundary, reading with a WRAP from the same
            # address with the same length returns the same sequence.
            # This RAM implementation does not support WRAP bursts and treats
            # them as INCR.
            expected_values = write_values

        read_values = await axim.read(address, burst_length, burst=burst,
                                      size=size)

        compare_read_values(expected_values, read_values, burst, burst_length,
                            address)


@cocotb.test()
async def test_narrow_burst(dut):
    """Test that narrow writes and full reads match"""

    axim = AXI4Master(dut, AXI_PREFIX, dut.clk)
    _, data_width, ram_start, ram_stop = get_parameters(dut)

    await setup_dut(dut)

    burst_length = (randrange(2, 256) // 2) * 2
    address = ram_start
    write_values = \
        [randrange(0, 2**(data_width * 8 // 2)) for i in range(burst_length)]

    await axim.write(address, write_values, size=data_width // 2)

    read_values = await axim.read(address, burst_length // 2)

    expected_values = [write_values[i + 1] << 16 | write_values[i]
                       for i in range(0, burst_length // 2, 2)]

    compare_read_values(expected_values, read_values, AXIBurst.INCR,
                        burst_length // 2, address)


async def test_unaligned(dut, size, burst):
    """Test that unaligned read and writes are performed correctly"""

    def get_random_words(length, size, num_bits):
        r_bytes = getrandbits(num_bits).to_bytes(size * length, 'little')
        r_words = [r_bytes[i * size:(i + 1) * size] for i in range(length)]
        r_ints = [int.from_bytes(w, 'little') for w in r_words]
        return r_bytes, r_ints

    axim = AXI4Master(dut, AXI_PREFIX, dut.clk)
    _, data_width, ram_start, ram_stop = get_parameters(dut)
    size = size if size else data_width

    await setup_dut(dut)

    burst_length = randrange(2, 16 if burst is AXIBurst.FIXED else 256)

    if burst is AXIBurst.FIXED:
        address = randrange(ram_start, ram_stop, size)
    else:
        base = randrange(ram_start, ram_stop, 4096)
        offset = randrange(0, 4096 - (burst_length - 1) * size, size)
        address = base + offset

    unaligned_addr = address + randrange(1, size)
    shift = unaligned_addr % size

    # Write aligned, read unaligned
    write_bytes, write_values = \
        get_random_words(burst_length, size, size * burst_length * 8)

    await axim.write(address, write_values, burst=burst, size=size)
    read_values = await axim.read(unaligned_addr, burst_length, burst=burst,
                                  size=size)

    if burst is AXIBurst.FIXED:
        mask = 2**((size - shift) * 8) - 1
        expected_values = \
            [(write_values[-1] >> (shift * 8)) & mask] * burst_length
    else:
        expected_bytes = write_bytes[shift:]
        expected_words = [expected_bytes[i * size:(i + 1) * size]
                          for i in range(burst_length)]
        expected_values = [int.from_bytes(w, 'little') for w in expected_words]

    compare_read_values(expected_values, read_values, burst, burst_length,
                        unaligned_addr)

    # Write unaligned, read aligned
    write_bytes, write_values = \
        get_random_words(burst_length, size,
                         (size * burst_length - shift) * 8)

    first_word = randrange(0, 2**(size * 8))
    await axim.write(address, first_word, burst=burst, size=size)
    await axim.write(unaligned_addr, write_values, burst=burst, size=size)
    read_values = await axim.read(address, burst_length, burst=burst,
                                  size=size)

    mask_low = 2**(shift * 8) - 1
    mask_high = (2**((size - shift) * 8) - 1) << (shift * 8)

    if burst is AXIBurst.FIXED:
        last_val = \
            first_word & mask_low | (write_values[-1] << shift * 8) & mask_high
        expected_values = [last_val] * burst_length
    else:
        first_bytes = (first_word & mask_low).to_bytes(shift, 'little')
        expected_bytes = first_bytes + write_bytes
        expected_words = [expected_bytes[i * size:(i + 1) * size]
                          for i in range(burst_length - 1)]
        expected_values = [int.from_bytes(w, 'little') for w in expected_words]

    compare_read_values(expected_values, read_values, burst, burst_length,
                        unaligned_addr)


async def test_unmapped(dut, driver):
    """Check whether a read/write over an unmapped address returns a DECERR"""

    axim = driver(dut, AXI_PREFIX, dut.clk)
    address_width, data_width, ram_start, ram_stop = get_parameters(dut)

    await setup_dut(dut)

    for rw in ("Read", "Write"):
        try:
            address = randrange(0, ram_start - data_width, data_width)
        except ValueError:
            # If the RAM is mapped at the beginning of the address space, use
            # an address after the end of the RAM
            address = randrange(ram_stop, 2**(address_width * 8) - data_width,
                                data_width)

        try:
            if rw == "Read":
                try:
                    await axim.read(address, length=2)
                except TypeError:
                    await axim.read(address)
            else:
                write_data = [randrange(0, 2**(data_width * 8))] * 2
                try:
                    await axim.write(address, write_data)
                except ValueError:
                    await axim.write(address, write_data[0])

            raise TestFailure("{} at {:#x} should have failed, but did not"
                              .format(rw, address))

        except AXIProtocolError as e:
            if e.xresp is not AXIxRESP.DECERR:
                raise TestFailure("Was expecting DECERR, but received {}"
                                  .format(e.xresp.name))


@cocotb.test()
async def test_illegal_operations(dut):
    """Test whether illegal operations are correctly refused by the driver"""

    axim = AXI4Master(dut, AXI_PREFIX, dut.clk)
    _, data_width, ram_start, _ = get_parameters(dut)

    illegal_operations = (
        (AXIBurst.INCR, -1, None),
        (AXIBurst.INCR, 0, None),
        (AXIBurst.FIXED, 17, None),
        (AXIBurst.INCR, 257, None),
        (AXIBurst.WRAP, 3, None),
        (AXIBurst.INCR, 4, -1),
        (AXIBurst.INCR, 4, data_width - 1),
        (AXIBurst.INCR, 4, data_width * 2),
    )

    await setup_dut(dut)

    for rw in ("Read", "Write"):
        for burst, length, size in illegal_operations:
            try:
                if rw == "Read":
                    await axim.read(ram_start, length, size=size, burst=burst)
                else:
                    values = [randrange(0, 2**(data_width * 8))
                              for i in range(length)]
                    await axim.write(ram_start, values, size=size, burst=burst)

                raise TestFailure(
                    "{} with length={}, size={} and burst={} has been "
                    "performed by the driver, but it is an illegal "
                    "operation".format(rw, length, size, burst.name))

            except ValueError:
                pass


@cocotb.test()
async def test_4kB_boundary(dut):
    """
    Check that the driver raises an error when trying to cross a 4kB boundary
    """

    axim = AXI4Master(dut, AXI_PREFIX, dut.clk)
    _, data_width, ram_start, ram_stop = get_parameters(dut)

    await setup_dut(dut)

    for rw in ("Read", "Write"):
        burst_length = randint(2, 256)
        base = randrange(ram_start, ram_stop - 4096, 4096)
        offset = randrange(-(burst_length - 1) * data_width, 0, data_width)
        address = base + offset
        write_values = \
            [randrange(0, 2**(data_width * 8)) for i in range(burst_length)]

        try:
            if rw == "Read":
                await axim.read(address, burst_length)
            else:
                await axim.write(address, write_values)

            raise TestFailure(
                "{} from {:#x} to {:#x} crosses a 4kB boundary, but the "
                "driver allowed it"
                .format(rw, address,
                        address + (burst_length - 1) * data_width))
        except ValueError:
            pass


async def test_simultaneous(dut, sync, num=5):
    """Test simultaneous reads/writes"""

    axim = AXI4Master(dut, AXI_PREFIX, dut.clk)
    _, data_width, ram_start, _ = get_parameters(dut)

    await setup_dut(dut)

    # Avoid crossing the 4kB boundary by using just the first 4kB block
    base_address = randrange(ram_start,
                             ram_start + 4096 - 2 * num * data_width,
                             data_width)

    # Clear the memory cells
    await axim.write(base_address, [0] * num)

    addresses = [base_address + i * data_width for i in range(num)]
    write_values = [randrange(0, 2**(data_width * 8)) for i in range(num)]

    writers = [axim.write(address, value, sync=sync)
               for address, value in zip(addresses, write_values)]

    await Combine(*writers)

    readers = [cocotb.fork(axim.read(address, sync=sync))
               for address in addresses]

    dummy_addrs = [base_address + (num + i) * data_width for i in range(num)]
    dummy_writers = [cocotb.fork(axim.write(address, value, sync=sync))
                     for address, value in zip(dummy_addrs, write_values)]

    read_values = []
    for reader in readers:
        read_values.append((await Join(reader))[0])
    await Combine(*[Join(writer) for writer in dummy_writers])

    for i, (written, read) in enumerate(zip(write_values, read_values)):
        if written != read:
            raise TestFailure("#{}: wrote {:#x} but read back {:#x}"
                              .format(i, written, read.integer))


@cocotb.test()
async def test_axi4lite_write_burst(dut):
    """Test that write bursts are correctly refused by the AXI4-Lite driver"""

    axim = AXI4LiteMaster(dut, AXI_PREFIX, dut.clk)
    _, data_width, ram_start, _ = get_parameters(dut)
    length = randint(2, 16)

    await setup_dut(dut)

    try:
        await axim.write(ram_start, [randrange(0, 2**(data_width * 8))
                                     for i in range(length)])

        raise TestFailure(
            "Write with length={} has been performed by the driver, but "
            "burst operations are not allowed on AXI4-Lite".format(length))

    except ValueError:
        pass


@cocotb.test()
async def test_read_length_mismatch(dut):
    """Test that a mismatch in the read data length is correctly identified"""

    class AXI4Master_unmanaged_arlen(AXI4Master):
        _signals = [signal for signal in AXI4Master._signals
                    if signal != "ARLEN"]

    axim = AXI4Master_unmanaged_arlen(dut, AXI_PREFIX, dut.clk)
    _, data_width, ram_start, ram_stop = get_parameters(dut)
    length = randint(2, 16)

    burst_length = randint(2, 255)
    base = randrange(ram_start, ram_stop, 4096)
    offset = randrange(0, 4096 - (burst_length - 1) * data_width, data_width)
    address = base + offset

    await setup_dut(dut)

    for length_delta in (-1, 1):
        try:
            # Override the driver's ARLEN value, forcing a wrong one
            await RisingEdge(dut.clk)
            arlen = burst_length - 1 + length_delta
            getattr(dut, AXI_PREFIX + '_ARLEN') <= arlen
            await axim.read(address, burst_length)

            raise TestFailure("Mismatch between ARLEN value ({}) and number "
                              "of read words ({}), but the driver did not "
                              "raise an exception"
                              .format(arlen, burst_length))

        except AXIReadBurstLengthMismatch:
            pass


single_beat = TestFactory(test_single_beat)
single_beat.add_option('driver', (AXI4Master, AXI4LiteMaster))
single_beat.add_option('address_latency', (0,))
single_beat.add_option('data_latency', (0,))
single_beat.generate_tests()

single_beat_with_latency = TestFactory(test_single_beat)
single_beat_with_latency.add_option('driver', (AXI4Master,))
single_beat_with_latency.add_option('address_latency', (0, 5))
single_beat_with_latency.add_option('data_latency', (1, 10))
single_beat_with_latency.generate_tests(postfix="_latency")

incr_burst = TestFactory(test_incr_burst)
incr_burst.add_option('return_rresp', (True, False))
incr_burst.add_option('size', (None,))
incr_burst.generate_tests()

incr_burst_size = TestFactory(test_incr_burst)
incr_burst_size.add_option('return_rresp', (False,))
incr_burst_size.add_option('size', (1, 2))
incr_burst_size.generate_tests(postfix="_size")

fixed_wrap_burst = TestFactory(test_fixed_wrap_burst)
fixed_wrap_burst.add_option('size', (None, 1, 2))
fixed_wrap_burst.generate_tests()

unaligned = TestFactory(test_unaligned)
unaligned.add_option('size', (None, 2))
unaligned.add_option('burst', (AXIBurst.FIXED, AXIBurst.INCR))
unaligned.generate_tests()

unmapped = TestFactory(test_unmapped)
unmapped.add_option('driver', [AXI4Master, AXI4LiteMaster])
unmapped.generate_tests()

simultaneous = TestFactory(test_simultaneous)
simultaneous.add_option('sync', [True, False])
simultaneous.generate_tests()
