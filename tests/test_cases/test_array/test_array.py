"""
A set of tests that demonstrate Array structure support
"""

import logging
import os

import cocotb
from cocotb.clock import Clock
from cocotb.handle import (
    ArrayObject,
    HierarchyArrayObject,
    HierarchyObject,
    LogicObject,
)
from cocotb.triggers import Timer

SIM_NAME = cocotb.SIM_NAME.lower()


def _check_type(tlog, hdl, expected):
    assert isinstance(hdl, expected), f">{hdl!r} ({hdl._type})< should be >{expected}<"
    tlog.info("   Found %r (%s)", hdl, hdl._type)


def _check_int(tlog, hdl, expected):
    assert hdl.value == expected, "{!r}: Expected >{}< but got >{}<".format(
        hdl, expected, hdl.value
    )
    tlog.info(f"   Found {hdl!r} ({hdl._type}) with value={hdl.value}")


def _check_logic(tlog, hdl, expected):
    assert hdl.value == expected, "{!r}: Expected >{}< but got >{}<".format(
        hdl, expected, hdl.value
    )
    tlog.info(f"   Found {hdl!r} ({hdl._type}) with value={hdl.value}")


def _check_str(tlog, hdl, expected):
    assert hdl.value == expected, "{!r}: Expected >{}< but got >{}<".format(
        hdl, expected, hdl.value
    )
    tlog.info(f"   Found {hdl!r} ({hdl._type}) with value={hdl.value}")


def _check_real(tlog, hdl, expected):
    assert hdl.value == expected, "{!r}: Expected >{}< but got >{}<".format(
        hdl, expected, hdl.value
    )
    tlog.info(f"   Found {hdl!r} ({hdl._type}) with value={hdl.value}")


def _check_value(tlog, hdl, expected):
    assert (
        hdl.value == expected
    ), f"{hdl!r}: Expected >{expected}< but got >{hdl.value}<"
    tlog.info(f"   Found {hdl!r} ({hdl._type}) with value={hdl.value}")


# NOTE: simulator-specific handling is done in this test itself, not via expect_error in the decorator
# GHDL unable to access std_logic_vector generics (gh-2593) (hard crash, so skip)
@cocotb.test(skip=SIM_NAME.startswith("ghdl"))
async def test_read_write(dut):
    """Test handle inheritance"""
    tlog = logging.getLogger("cocotb.test")

    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())

    await Timer(10, "ns")

    tlog.info("Checking Generics/Parameters:")
    _check_logic(tlog, dut.param_logic, 1)
    _check_logic(tlog, dut.param_logic_vec, 0xDA)

    if cocotb.LANGUAGE in ["vhdl"]:
        _check_int(tlog, dut.param_bool, 1)
        _check_int(tlog, dut.param_int, 6)
        _check_real(tlog, dut.param_real, 3.14)
        _check_int(tlog, dut.param_char, ord("p"))
        _check_str(tlog, dut.param_str, b"ARRAYMOD")

        if not cocotb.SIM_NAME.lower().startswith("riviera"):
            _check_logic(tlog, dut.param_rec.a, 0)
            _check_logic(tlog, dut.param_rec.b[0], 0)
            _check_logic(tlog, dut.param_rec.b[1], 0)
            _check_logic(tlog, dut.param_rec.b[2], 0)
            _check_logic(tlog, dut.param_cmplx[0].a, 0)
            _check_logic(tlog, dut.param_cmplx[0].b[0], 0)
            _check_logic(tlog, dut.param_cmplx[0].b[1], 0)
            _check_logic(tlog, dut.param_cmplx[0].b[2], 0)
            _check_logic(tlog, dut.param_cmplx[1].a, 0)
            _check_logic(tlog, dut.param_cmplx[1].b[0], 0)
            _check_logic(tlog, dut.param_cmplx[1].b[1], 0)
            _check_logic(tlog, dut.param_cmplx[1].b[2], 0)

    tlog.info("Checking Constants:")
    _check_logic(tlog, dut.const_logic, 0)
    _check_logic(tlog, dut.const_logic_vec, 0x3D)

    if cocotb.LANGUAGE in ["vhdl"]:
        _check_int(tlog, dut.const_bool, 0)
        _check_int(tlog, dut.const_int, 12)
        _check_real(tlog, dut.const_real, 6.28)
        _check_int(tlog, dut.const_char, ord("c"))
        _check_str(tlog, dut.const_str, b"MODARRAY")

        if not cocotb.SIM_NAME.lower().startswith("riviera"):
            _check_logic(tlog, dut.const_rec.a, 1)
            _check_logic(tlog, dut.const_rec.b[0], 0xFF)
            _check_logic(tlog, dut.const_rec.b[1], 0xFF)
            _check_logic(tlog, dut.const_rec.b[2], 0xFF)
            _check_logic(tlog, dut.const_cmplx[1].a, 1)
            _check_logic(tlog, dut.const_cmplx[1].b[0], 0xFF)
            _check_logic(tlog, dut.const_cmplx[1].b[1], 0xFF)
            _check_logic(tlog, dut.const_cmplx[1].b[2], 0xFF)
            _check_logic(tlog, dut.const_cmplx[2].a, 1)
            _check_logic(tlog, dut.const_cmplx[2].b[0], 0xFF)
            _check_logic(tlog, dut.const_cmplx[2].b[1], 0xFF)
            _check_logic(tlog, dut.const_cmplx[2].b[2], 0xFF)

    dut.select_in.value = 2

    await Timer(10, "ns")

    tlog.info("Writing the signals!!!")
    dut.sig_logic.value = 1
    dut.sig_logic_vec.value = 0xCC
    dut.sig_t2.value = [0xCC, 0xDD, 0xEE, 0xFF]
    dut.sig_t4.value = [
        [0x00, 0x11, 0x22, 0x33],
        [0x44, 0x55, 0x66, 0x77],
        [0x88, 0x99, 0xAA, 0xBB],
        [0xCC, 0xDD, 0xEE, 0xFF],
    ]

    if cocotb.LANGUAGE in ["vhdl"]:
        dut.sig_bool.value = 1
        dut.sig_int.value = 5000
        dut.sig_real.value = 22.54
        dut.sig_char.value = ord("Z")
        dut.sig_str.value = b"Testing"
        dut.sig_rec.a.value = 1
        dut.sig_rec.b[0].value = 0x01
        dut.sig_rec.b[1].value = 0x23
        dut.sig_rec.b[2].value = 0x45
        dut.sig_cmplx[0].a.value = 0
        dut.sig_cmplx[0].b[0].value = 0x67
        dut.sig_cmplx[0].b[1].value = 0x89
        dut.sig_cmplx[0].b[2].value = 0xAB
        dut.sig_cmplx[1].a.value = 1
        dut.sig_cmplx[1].b[0].value = 0xCD
        dut.sig_cmplx[1].b[1].value = 0xEF
        dut.sig_cmplx[1].b[2].value = 0x55

    await Timer(10, "ns")

    tlog.info("Checking writes:")
    _check_logic(tlog, dut.port_logic_out, 1)
    _check_logic(tlog, dut.port_logic_vec_out, 0xCC)
    # Some writes to multi-dimensional arrays don't make it into the design.
    # https://github.com/cocotb/cocotb/issues/3372
    if not cocotb.SIM_NAME.startswith("xmsim"):
        _check_value(tlog, dut.sig_t2, [0xCC, 0xDD, 0xEE, 0xFF])
        _check_logic(tlog, dut.sig_t2[7], 0xCC)
        _check_logic(tlog, dut.sig_t2[4], 0xFF)
        _check_logic(tlog, dut.sig_t4[1][5], 0x66)
        _check_logic(tlog, dut.sig_t4[3][7], 0xCC)

    if cocotb.LANGUAGE in ["vhdl"]:
        _check_int(tlog, dut.port_bool_out, 1)
        _check_int(tlog, dut.port_int_out, 5000)
        _check_real(tlog, dut.port_real_out, 22.54)
        _check_int(tlog, dut.port_char_out, ord("Z"))
        _check_str(tlog, dut.port_str_out, b"Testing")

        _check_logic(tlog, dut.port_rec_out.a, 1)
        _check_logic(tlog, dut.port_rec_out.b[0], 0x01)
        _check_logic(tlog, dut.port_rec_out.b[1], 0x23)
        _check_logic(tlog, dut.port_rec_out.b[2], 0x45)
        _check_logic(tlog, dut.port_cmplx_out[0].a, 0)
        _check_logic(tlog, dut.port_cmplx_out[0].b[0], 0x67)
        _check_logic(tlog, dut.port_cmplx_out[0].b[1], 0x89)
        _check_logic(tlog, dut.port_cmplx_out[0].b[2], 0xAB)
        _check_logic(tlog, dut.port_cmplx_out[1].a, 1)
        _check_logic(tlog, dut.port_cmplx_out[1].b[0], 0xCD)
        _check_logic(tlog, dut.port_cmplx_out[1].b[1], 0xEF)
        _check_logic(tlog, dut.port_cmplx_out[1].b[2], 0x55)

    tlog.info("Writing a few signal sub-indices!!!")
    dut.sig_logic_vec[2].value = 0
    if cocotb.LANGUAGE in ["vhdl"] or not (
        cocotb.SIM_NAME.lower().startswith(("ncsim", "xmsim"))
        or (
            cocotb.SIM_NAME.lower().startswith("riviera")
            and cocotb.SIM_VERSION.startswith(("2016.06", "2016.10", "2017.02"))
        )
    ):
        dut.sig_t6[1][3][2].value = 1
        dut.sig_t6[0][2][7].value = 0

    if cocotb.LANGUAGE in ["vhdl"]:
        dut.sig_str[2].value = ord("E")
        dut.sig_rec.b[1][7].value = 1
        dut.sig_cmplx[1].b[1][0].value = 0

    await Timer(10, "ns")

    tlog.info("Checking writes (2):")
    _check_logic(tlog, dut.port_logic_vec_out, 0xC8)
    if cocotb.LANGUAGE in ["vhdl"] or not (
        cocotb.SIM_NAME.lower().startswith(("ncsim", "xmsim"))
        or (
            cocotb.SIM_NAME.lower().startswith("riviera")
            and cocotb.SIM_VERSION.startswith(("2016.06", "2016.10", "2017.02"))
        )
    ):
        _check_logic(tlog, dut.sig_t6[1][3][2], 1)
        _check_logic(tlog, dut.sig_t6[0][2][7], 0)

    if cocotb.LANGUAGE in ["vhdl"]:
        _check_str(
            tlog, dut.port_str_out, b"TEsting"
        )  # the uppercase "E" from a few lines before

        _check_logic(tlog, dut.port_rec_out.b[1], 0xA3)
        _check_logic(tlog, dut.port_cmplx_out[1].b[1], 0xEE)


# GHDL unable to access signals in generate loops (gh-2594)
@cocotb.test(expect_error=IndexError if SIM_NAME.startswith("ghdl") else ())
async def test_gen_loop(dut):
    """Test accessing Generate Loops"""
    tlog = logging.getLogger("cocotb.test")

    asc_gen_20 = dut.asc_gen[20]
    desc_gen = dut.desc_gen

    assert isinstance(dut.asc_gen, HierarchyArrayObject)
    assert isinstance(desc_gen, HierarchyArrayObject)
    assert isinstance(asc_gen_20, HierarchyObject)

    tlog.info("Direct access found %s", asc_gen_20)
    tlog.info("Direct access found %s", desc_gen)

    for gens in desc_gen:
        tlog.info("Iterate access found %s", gens)

    assert len(desc_gen) == 8
    tlog.info("Length of desc_gen is %d", len(desc_gen))

    assert len(dut.asc_gen) == 8
    tlog.info("Length of asc_gen is %d", len(dut.asc_gen))

    for gens in dut.asc_gen:
        tlog.info("Iterate access found %s", gens)


@cocotb.test()
async def test_discover_all(dut):
    r"""Discover everything in the DUT:
    dut
           TYPE    CNT  NOTES                                                  EXCEPTIONS
       parameters: 7/2 (base types)                                            (VHDL/Verilog)
                     6 (param_rec.a, param_rec.b[0:2])                         (VHDL Only)
                    13 (param_cmplx[0:1].a, param_cmplx[0:1].b[0:2])           (VHDL Only)
            ports:   1 (clk)
                     1 (select_in)                                             (VPI - Aldec sees as 32 bit register (i.e. cnt = 33)
                     9 (port_desc_in)
                     9 (port_asc_in)
                     9 (port_ofst_in)
                     9 (port_desc_out)
                     9 (port_asc_out)
                     9 (port_ofst_out)
                     1 (port_logic_out)
                     9 (port_logic_vec_out)
                     1 (port_bool_out)                                         (VHDL Only)
                     1 (port_int_out)                                          (VHDL Only)
                     1 (port_real_out)                                         (VHDL Only)
                     1 (port_char_out)                                         (VHDL Only)
                     9 (port_str_out)                                          (VHDL Only)
                    30 (port_rec_out)                                          (VPI - Aldec sees as a Module and not structure (i.e. cnt = 1))
                    61 (port_cmplx_out)                                        (VPI - Aldec sees as a Module and not structure (i.e. cnt = 1))
        constants:   1 (const_logic)
                     9 (const_logic_vec)
                     1 (const_bool)                                            (VHDL Only)
                     1 (const_int)                                             (VHDL Only)
                     1 (const_real)                                            (VHDL Only)
                     1 (const_char)                                            (VHDL Only)
                     9 (const_str)                                             (VHDL Only)
                     1 (const_rec)                                             (VHDL Only)
                     1 (const_rec.a)                                           (VHDL Only)
                     1 (const_rec.b)                                           (VHDL Only)
                     9 (const_rec.b[0])                                        (VHDL Only)
                     9 (const_rec.b[1])                                        (VHDL Only)
                     9 (const_rec.b[2])                                        (VHDL Only)
                     1 (const_cmplx)                                           (VHDL Only)
                     1 (const_cmplx[1])                                        (VHDL Only)
                     1 (const_cmplx[1].a)                                      (VHDL Only)
                     1 (const_cmplx[1].b)                                      (VHDL Only)
                     9 (const_cmplx[1].b[0])                                   (VHDL Only)
                     9 (const_cmplx[1].b[1])                                   (VHDL Only)
                     9 (const_cmplx[1].b[2])                                   (VHDL Only)
                     1 (const_cmplx[2])                                        (VHDL Only)
                     1 (const_cmplx[2].a)                                      (VHDL Only)
                     1 (const_cmplx[2].b)                                      (VHDL Only)
                     9 (const_cmplx[2].b[0])                                   (VHDL Only)
                     9 (const_cmplx[2].b[1])                                   (VHDL Only)
                     9 (const_cmplx[2].b[2])                                   (VHDL Only)
          signals:   9 (sig_desc)
                     9 (sig_asc)
                     1 (\ext_id\)                                              (VHDL Only)
                     1 (\!\)                                                   (VHDL Only)
                     5 (sig_t1)
                    37 (sig_t2[7:4][7:0])
                    37 (sig_t3a[1:4][7:0])
                    37 (sig_t3b[3:0][7:0])
                   149 (sig_t4[0:3][7:4][7:0])
                   112 (sig_t5[0:2][0:3][7:0])
                    57 (sig_t6[0:1][2:4][7:0])
                   149 (sig_t7[3:0][3:0])                                      (VPI Only)
                   149 ([3:0][3:0]sig_t8)                                      (VPI Only)
                     1 (sig_logic)
                     9 (sig_logic_vec)
                     1 (sig_bool)                                              (VHDL Only)
                     1 (sig_int)                                               (VHDL Only)
                     1 (sig_real)                                              (VHDL Only)
                     1 (sig_char)                                              (VHDL Only)
                     9 (sig_str)                                               (VHDL Only)
                    30 (sig_rec.a, sig_rec.b[0:2][7:0])                        (VPI doesn't find, added manually, except for Aldec)
                    61 (sig_cmplx[0:1].a, sig_cmplx[0:1].b[0:2][7:0])          (VPI - Aldec older than 2017.10.67 doesn't find)
          regions:   9 (asc_gen[16:23])
                     8 (asc_gen: signals)
                     8 (asc_gen: constant)
                     8 (asc_gen: variable)
                     8 (asc_gen: process "always")                             (VPI - Aldec only)
                     9 (desc_gen[7:0])
                     8 (desc_gen: signals)
                     8 (desc_gen: constant)
                     8 (desc_gen: variable)
                     8 (desc_gen: process "always")                            (VPI - Aldec only)
          process:   1 ("always")                                              (VPI - Aldec only)

            TOTAL: 1032 (VHDL - Default)
                    818 (VHDL - Aldec)
                   1078 (Verilog - Default)
               947/1038 (Verilog - Aldec)
    """

    tlog = logging.getLogger("cocotb.test")

    await Timer(10, "ns")

    # Need to clear sub_handles so won't attempt to iterate over handles like sig_rec and sig_rec_array
    #
    # DO NOT REMOVE.  Aldec cannot iterate over the complex records due to bugs in the VPI interface.
    if (
        cocotb.LANGUAGE in ["verilog"]
        and cocotb.SIM_NAME.lower().startswith("riviera")
        and cocotb.SIM_VERSION.startswith("2016.02")
    ):
        if len(dut._sub_handles) != 0:
            dut._sub_handles = {}

    # Modelsim/Questa VPI will not find a vpiStructVar from vpiModule so we access them explicitly
    # to ensure the handle is in the dut "sub_handles" for iterating
    #
    # DO NOT ADD FOR ALDEC.  Older Versions do not iterate over properly
    if cocotb.LANGUAGE in ["verilog"] and cocotb.SIM_NAME.lower().startswith(
        ("modelsim", "ncsim", "xmsim")
    ):
        dut.sig_rec
        dut.port_rec_out

    if cocotb.SIM_NAME.lower().startswith("ghdl"):
        pass_total = 56
    elif (
        cocotb.LANGUAGE in ["vhdl"]
        and cocotb.SIM_NAME.lower().startswith("modelsim")
        and os.environ["VHDL_GPI_INTERFACE"] == "vhpi"
    ):
        # VHPI finds the array_module.asc_gen and array_module.desc_gen more than once =/
        pass_total = 1096
    elif cocotb.LANGUAGE in ["vhdl"]:
        pass_total = 1032
    elif cocotb.LANGUAGE in ["verilog"] and cocotb.SIM_NAME.lower().startswith(
        "riviera"
    ):
        # Applies to Riviera-PRO 2019.10 and newer.
        pass_total = 1006
    elif cocotb.LANGUAGE in ["verilog"] and cocotb.SIM_NAME.lower().startswith(
        "chronologic simulation vcs"
    ):
        pass_total = 606
    else:
        pass_total = 1078

    def _discover(obj):
        if not isinstance(
            obj,
            (
                cocotb.handle.HierarchyObjectBase,
                cocotb.handle.IndexableValueObjectBase,
            ),
        ):
            return 0
        count = 0
        for thing in obj:
            count += 1
            tlog.info("Found %s (%s)", thing._path, type(thing))
            count += _discover(thing)
        return count

    tlog.info("Iterating over %r (%s)", dut, dut._type)
    total = _discover(dut)
    tlog.info("Found a total of %d things", total)
    assert total == pass_total


# GHDL unable to access std_logic_vector generics (gh-2593)
@cocotb.test(
    skip=(
        cocotb.LANGUAGE in ["verilog"] or cocotb.SIM_NAME.lower().startswith("riviera")
    ),
    expect_error=AttributeError if SIM_NAME.startswith("ghdl") else (),
)
async def test_direct_constant_indexing(dut):
    """Test directly accessing constant/parameter data in arrays, i.e. not iterating"""

    tlog = logging.getLogger("cocotb.test")

    tlog.info("Checking Types of complex array structures in constants/parameters.")
    _check_type(tlog, dut.param_rec, HierarchyObject)
    _check_type(tlog, dut.param_rec.a, LogicObject)
    _check_type(tlog, dut.param_rec.b, ArrayObject)
    _check_type(tlog, dut.param_rec.b[1], LogicObject)

    _check_type(tlog, dut.param_cmplx, ArrayObject)
    _check_type(tlog, dut.param_cmplx[0], HierarchyObject)
    _check_type(tlog, dut.param_cmplx[0].a, LogicObject)
    _check_type(tlog, dut.param_cmplx[0].b, ArrayObject)
    _check_type(tlog, dut.param_cmplx[0].b[1], LogicObject)

    _check_type(tlog, dut.const_rec, HierarchyObject)
    _check_type(tlog, dut.const_rec.a, LogicObject)
    _check_type(tlog, dut.const_rec.b, ArrayObject)
    _check_type(tlog, dut.const_rec.b[1], LogicObject)

    _check_type(tlog, dut.const_cmplx, ArrayObject)
    _check_type(tlog, dut.const_cmplx[1], HierarchyObject)
    _check_type(tlog, dut.const_cmplx[1].a, LogicObject)
    _check_type(tlog, dut.const_cmplx[1].b, ArrayObject)
    _check_type(tlog, dut.const_cmplx[1].b[1], LogicObject)


# GHDL unable to index packed arrays (gh-2587)
@cocotb.test(expect_error=IndexError if SIM_NAME.startswith("ghdl") else ())
async def test_direct_signal_indexing(dut):
    """Test directly accessing signal/net data in arrays, i.e. not iterating"""

    tlog = logging.getLogger("cocotb.test")

    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())

    dut.port_desc_in.value = 0
    dut.port_asc_in.value = 0
    dut.port_ofst_in.value = 0

    await Timer(20, "ns")

    dut.port_desc_in[2].value = 1
    dut.port_asc_in[2].value = 1
    dut.port_ofst_in[2].value = 1

    await Timer(20, "ns")

    tlog.info("Checking bit mapping from input to generate loops.")
    assert dut.desc_gen[2].sig.value == 1
    tlog.info("   %r = %d", dut.desc_gen[2].sig, dut.desc_gen[2].sig.value)

    assert dut.asc_gen[18].sig.value == 1
    tlog.info("   %r = %d", dut.asc_gen[18].sig, dut.asc_gen[18].sig.value)

    tlog.info("Checking indexing of data with offset index.")
    assert dut.port_ofst_out.value == 64
    tlog.info(
        "   %r = %d (%s)",
        dut.port_ofst_out,
        dut.port_ofst_out.value,
        dut.port_ofst_out.value.binstr,
    )

    tlog.info("Checking Types of complex array structures in signals.")
    _check_type(tlog, dut.sig_desc[20], LogicObject)
    _check_type(tlog, dut.sig_asc[17], LogicObject)
    _check_type(tlog, dut.sig_t1, LogicObject)
    _check_type(tlog, dut.sig_t2, ArrayObject)
    _check_type(tlog, dut.sig_t2[5], LogicObject)
    _check_type(tlog, dut.sig_t2[5][3], LogicObject)
    _check_type(tlog, dut.sig_t3a[2][3], LogicObject)
    _check_type(tlog, dut.sig_t3b[3], LogicObject)
    _check_type(tlog, dut.sig_t3a, ArrayObject)
    _check_type(tlog, dut.sig_t4, ArrayObject)
    _check_type(tlog, dut.sig_t4[3], ArrayObject)
    # the following version cannot index into those arrays and will error out
    if not (
        cocotb.LANGUAGE in ["verilog"]
        and cocotb.SIM_NAME.lower().startswith("riviera")
        and cocotb.SIM_VERSION.startswith(("2016.06", "2016.10", "2017.02"))
    ):
        _check_type(tlog, dut.sig_t4[3][4], LogicObject)
        _check_type(tlog, dut.sig_t4[3][4][1], LogicObject)
    _check_type(tlog, dut.sig_t5, ArrayObject)
    _check_type(tlog, dut.sig_t5[1], ArrayObject)
    _check_type(tlog, dut.sig_t5[1][0], LogicObject)
    _check_type(tlog, dut.sig_t5[1][0][6], LogicObject)
    _check_type(tlog, dut.sig_t6, ArrayObject)
    _check_type(tlog, dut.sig_t6[1], ArrayObject)
    # the following version cannot index into those arrays and will error out
    if not (
        cocotb.LANGUAGE in ["verilog"]
        and cocotb.SIM_NAME.lower().startswith("riviera")
        and cocotb.SIM_VERSION.startswith(("2016.06", "2016.10", "2017.02"))
    ):
        _check_type(tlog, dut.sig_t6[0][3], LogicObject)
        _check_type(tlog, dut.sig_t6[0][3][7], LogicObject)
    _check_type(tlog, dut.sig_cmplx, ArrayObject)

    if cocotb.LANGUAGE in ["verilog"]:
        _check_type(tlog, dut.sig_t7[1], ArrayObject)
        _check_type(tlog, dut.sig_t7[0][3], LogicObject)
        _check_type(
            tlog, dut.sig_t8[1], LogicObject
        )  # packed array of logic is mapped to GPI_NET
        _check_type(tlog, dut.sig_t8[0][3], LogicObject)

    # Riviera has a bug and finds dut.sig_cmplx[1], but the type returned is a vpiBitVar
    # only true for version 2016.02
    if not (
        cocotb.LANGUAGE in ["verilog"]
        and cocotb.SIM_NAME.lower().startswith("riviera")
        and cocotb.SIM_VERSION.startswith("2016.02")
    ):
        _check_type(tlog, dut.sig_cmplx[1], HierarchyObject)
        _check_type(tlog, dut.sig_cmplx[1].a, LogicObject)
        _check_type(tlog, dut.sig_cmplx[1].b, ArrayObject)
        _check_type(tlog, dut.sig_cmplx[1].b[1], LogicObject)
        _check_type(tlog, dut.sig_cmplx[1].b[1][2], LogicObject)

    _check_type(tlog, dut.sig_rec, HierarchyObject)
    _check_type(tlog, dut.sig_rec.a, LogicObject)
    _check_type(tlog, dut.sig_rec.b, ArrayObject)

    # Riviera has a bug and finds dut.sig_rec.b[1], but the type returned is 0 which is unknown
    # only true for version 2016.02
    if not (
        cocotb.LANGUAGE in ["verilog"]
        and cocotb.SIM_NAME.lower().startswith("riviera")
        and cocotb.SIM_VERSION.startswith("2016.02")
    ):
        _check_type(tlog, dut.sig_rec.b[1], LogicObject)
        _check_type(tlog, dut.sig_rec.b[1][2], LogicObject)


@cocotb.test(skip=(cocotb.LANGUAGE in ["verilog"]))
async def test_extended_identifiers(dut):
    """Test accessing extended identifiers"""

    tlog = logging.getLogger("cocotb.test")
    tlog.info("Checking extended identifiers.")
    _check_type(tlog, dut["\\ext_id\\"], LogicObject)
    _check_type(tlog, dut["\\!\\"], LogicObject)
