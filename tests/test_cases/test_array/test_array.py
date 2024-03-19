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
    HierarchyObjectBase,
    IndexableValueObjectBase,
    LogicObject,
)
from cocotb.triggers import Timer

SIM_NAME = cocotb.SIM_NAME.lower()
LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()


# NOTE: simulator-specific handling is done in this test itself, not via expect_error in the decorator
# GHDL unable to access std_logic_vector generics (gh-2593) (hard crash, so skip)
@cocotb.test(skip=SIM_NAME.startswith("ghdl"))
async def test_read_write(dut):
    """Test handle inheritance"""

    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())

    await Timer(10, "ns")

    assert dut.param_logic.value == 1
    assert dut.param_logic_vec.value == 0xDA

    if LANGUAGE in ["vhdl"]:
        assert dut.param_bool.value == 1
        assert dut.param_int.value == 6
        assert dut.param_real.value == 3.14
        assert dut.param_char.value == ord("p")
        assert dut.param_str.value == b"ARRAYMOD"

        if not cocotb.SIM_NAME.lower().startswith("riviera"):
            assert dut.param_rec.a.value == 0
            assert dut.param_rec.b[0].value == 0
            assert dut.param_rec.b[1].value == 0
            assert dut.param_rec.b[2].value == 0
            assert dut.param_cmplx[0].a.value == 0
            assert dut.param_cmplx[0].b[0].value == 0
            assert dut.param_cmplx[0].b[1].value == 0
            assert dut.param_cmplx[0].b[2].value == 0
            assert dut.param_cmplx[1].a.value == 0
            assert dut.param_cmplx[1].b[0].value == 0
            assert dut.param_cmplx[1].b[1].value == 0
            assert dut.param_cmplx[1].b[2].value == 0

    assert dut.const_logic.value == 0
    assert dut.const_logic_vec.value == 0x3D

    if LANGUAGE in ["vhdl"]:
        assert dut.const_bool.value == 0
        assert dut.const_int.value == 12
        assert dut.const_real.value == 6.28
        assert dut.const_char.value == ord("c")
        assert dut.const_str.value == b"MODARRAY"

        if not cocotb.SIM_NAME.lower().startswith("riviera"):
            assert dut.const_rec.a.value == 1
            assert dut.const_rec.b[0].value == 0xFF
            assert dut.const_rec.b[1].value == 0xFF
            assert dut.const_rec.b[2].value == 0xFF
            assert dut.const_cmplx[1].a.value == 1
            assert dut.const_cmplx[1].b[0].value == 0xFF
            assert dut.const_cmplx[1].b[1].value == 0xFF
            assert dut.const_cmplx[1].b[2].value == 0xFF
            assert dut.const_cmplx[2].a.value == 1
            assert dut.const_cmplx[2].b[0].value == 0xFF
            assert dut.const_cmplx[2].b[1].value == 0xFF
            assert dut.const_cmplx[2].b[2].value == 0xFF

    dut.select_in.value = 2

    await Timer(10, "ns")

    dut.sig_logic.value = 1
    dut.sig_logic_vec.value = 0xCC
    dut.sig_t2.value = [0xCC, 0xDD, 0xEE, 0xFF]
    dut.sig_t4.value = [
        [0x00, 0x11, 0x22, 0x33],
        [0x44, 0x55, 0x66, 0x77],
        [0x88, 0x99, 0xAA, 0xBB],
        [0xCC, 0xDD, 0xEE, 0xFF],
    ]

    if LANGUAGE in ["vhdl"]:
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

    assert dut.port_logic_out.value == 1
    assert dut.port_logic_vec_out.value == 0xCC
    # Some writes to multi-dimensional arrays don't make it into the design.
    # https://github.com/cocotb/cocotb/issues/3372
    if not cocotb.SIM_NAME.startswith("xmsim"):
        assert dut.sig_t2.value == [0xCC, 0xDD, 0xEE, 0xFF]
        assert dut.sig_t2[7].value == 0xCC
        assert dut.sig_t2[4].value == 0xFF
        assert dut.sig_t4[1][5].value == 0x66
        assert dut.sig_t4[3][7].value == 0xCC

    if LANGUAGE in ["vhdl"]:
        assert dut.port_bool_out.value == 1
        assert dut.port_int_out.value == 5000
        assert dut.port_real_out.value == 22.54
        assert dut.port_char_out.value == ord("Z")
        assert dut.port_str_out.value == b"Testing"

        assert dut.port_rec_out.a.value == 1
        assert dut.port_rec_out.b[0].value == 0x01
        assert dut.port_rec_out.b[1].value == 0x23
        assert dut.port_rec_out.b[2].value == 0x45
        assert dut.port_cmplx_out[0].a.value == 0
        assert dut.port_cmplx_out[0].b[0].value == 0x67
        assert dut.port_cmplx_out[0].b[1].value == 0x89
        assert dut.port_cmplx_out[0].b[2].value == 0xAB
        assert dut.port_cmplx_out[1].a.value == 1
        assert dut.port_cmplx_out[1].b[0].value == 0xCD
        assert dut.port_cmplx_out[1].b[1].value == 0xEF
        assert dut.port_cmplx_out[1].b[2].value == 0x55

    dut.sig_logic_vec[2].value = 0
    if LANGUAGE in ["vhdl"] or not (
        cocotb.SIM_NAME.lower().startswith(("ncsim", "xmsim"))
        or (
            cocotb.SIM_NAME.lower().startswith("riviera")
            and cocotb.SIM_VERSION.startswith(("2016.06", "2016.10", "2017.02"))
        )
    ):
        dut.sig_t6[1][3][2].value = 1
        dut.sig_t6[0][2][7].value = 0

    if LANGUAGE in ["vhdl"]:
        dut.sig_str[2].value = ord("E")
        dut.sig_rec.b[1][7].value = 1
        dut.sig_cmplx[1].b[1][0].value = 0

    await Timer(10, "ns")

    assert dut.port_logic_vec_out.value == 0xC8
    if LANGUAGE in ["vhdl"] or not (
        cocotb.SIM_NAME.lower().startswith(("ncsim", "xmsim"))
        or (
            cocotb.SIM_NAME.lower().startswith("riviera")
            and cocotb.SIM_VERSION.startswith(("2016.06", "2016.10", "2017.02"))
        )
    ):
        assert dut.sig_t6[1][3][2].value == 1
        assert dut.sig_t6[0][2][7].value == 0

    if LANGUAGE in ["vhdl"]:
        assert (
            dut.port_str_out.value == b"TEsting"
        )  # the uppercase "E" from a few lines before

        assert dut.port_rec_out.b[1].value == 0xA3
        assert dut.port_cmplx_out[1].b[1].value == 0xEE


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
        LANGUAGE in ["verilog"]
        and cocotb.SIM_NAME.lower().startswith("riviera")
        and cocotb.SIM_VERSION.startswith("2016.02")
    ):
        if len(dut._sub_handles) != 0:
            dut._sub_handles = {}

    # Modelsim/Questa VPI will not find a vpiStructVar from vpiModule so we access them explicitly
    # to ensure the handle is in the dut "sub_handles" for iterating
    #
    # DO NOT ADD FOR ALDEC.  Older Versions do not iterate over properly
    if LANGUAGE in ["verilog"] and cocotb.SIM_NAME.lower().startswith(
        ("modelsim", "ncsim", "xmsim")
    ):
        dut.sig_rec
        dut.port_rec_out

    if cocotb.SIM_NAME.lower().startswith("ghdl"):
        pass_total = 56
    elif (
        LANGUAGE in ["vhdl"]
        and cocotb.SIM_NAME.lower().startswith("modelsim")
        and os.environ["VHDL_GPI_INTERFACE"] == "vhpi"
    ):
        # VHPI finds the array_module.asc_gen and array_module.desc_gen more than once =/
        pass_total = 1096
    elif LANGUAGE in ["vhdl"]:
        pass_total = 1032
    elif LANGUAGE in ["verilog"] and cocotb.SIM_NAME.lower().startswith("riviera"):
        # Applies to Riviera-PRO 2019.10 and newer.
        pass_total = 1006
    elif LANGUAGE in ["verilog"] and cocotb.SIM_NAME.lower().startswith(
        "chronologic simulation vcs"
    ):
        pass_total = 606
    else:
        pass_total = 1078

    def _discover(obj):
        if not isinstance(
            obj,
            (
                HierarchyObjectBase,
                IndexableValueObjectBase,
            ),
        ):
            return 0
        count = 0
        for thing in obj:
            count += 1
            tlog.info("Found %s (%s)", thing._path, type(thing))
            count += _discover(thing)
        return count

    total = _discover(dut)
    tlog.info("Found a total of %d things", total)
    assert total == pass_total


# GHDL unable to access std_logic_vector generics (gh-2593)
@cocotb.test(
    skip=(LANGUAGE in ["verilog"] or cocotb.SIM_NAME.lower().startswith("riviera")),
    expect_error=AttributeError if SIM_NAME.startswith("ghdl") else (),
)
async def test_direct_constant_indexing(dut):
    """Test directly accessing constant/parameter data in arrays, i.e. not iterating"""

    assert isinstance(dut.param_rec, HierarchyObject)
    assert isinstance(dut.param_rec.a, LogicObject)
    assert isinstance(dut.param_rec.b, ArrayObject)
    assert isinstance(dut.param_rec.b[1], LogicObject)

    assert isinstance(dut.param_cmplx, ArrayObject)
    assert isinstance(dut.param_cmplx[0], HierarchyObject)
    assert isinstance(dut.param_cmplx[0].a, LogicObject)
    assert isinstance(dut.param_cmplx[0].b, ArrayObject)
    assert isinstance(dut.param_cmplx[0].b[1], LogicObject)

    assert isinstance(dut.const_rec, HierarchyObject)
    assert isinstance(dut.const_rec.a, LogicObject)
    assert isinstance(dut.const_rec.b, ArrayObject)
    assert isinstance(dut.const_rec.b[1], LogicObject)

    assert isinstance(dut.const_cmplx, ArrayObject)
    assert isinstance(dut.const_cmplx[1], HierarchyObject)
    assert isinstance(dut.const_cmplx[1].a, LogicObject)
    assert isinstance(dut.const_cmplx[1].b, ArrayObject)
    assert isinstance(dut.const_cmplx[1].b[1], LogicObject)


# GHDL unable to index packed arrays (gh-2587)
@cocotb.test(expect_error=IndexError if SIM_NAME.startswith("ghdl") else ())
async def test_direct_signal_indexing(dut):
    """Test directly accessing signal/net data in arrays, i.e. not iterating"""

    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())

    dut.port_desc_in.value = 0
    dut.port_asc_in.value = 0
    dut.port_ofst_in.value = 0

    await Timer(20, "ns")

    dut.port_desc_in[2].value = 1
    dut.port_asc_in[2].value = 1
    dut.port_ofst_in[2].value = 1

    await Timer(20, "ns")

    assert dut.desc_gen[2].sig.value == 1
    assert dut.asc_gen[18].sig.value == 1
    assert dut.port_ofst_out.value == 64

    assert isinstance(dut.sig_desc[20], LogicObject)
    assert isinstance(dut.sig_asc[17], LogicObject)
    assert isinstance(dut.sig_t1, LogicObject)
    assert isinstance(dut.sig_t2, ArrayObject)
    assert isinstance(dut.sig_t2[5], LogicObject)
    assert isinstance(dut.sig_t2[5][3], LogicObject)
    assert isinstance(dut.sig_t3a[2][3], LogicObject)
    assert isinstance(dut.sig_t3b[3], LogicObject)
    assert isinstance(dut.sig_t3a, ArrayObject)
    assert isinstance(dut.sig_t4, ArrayObject)
    assert isinstance(dut.sig_t4[3], ArrayObject)
    # the following version cannot index into those arrays and will error out
    if not (
        LANGUAGE in ["verilog"]
        and cocotb.SIM_NAME.lower().startswith("riviera")
        and cocotb.SIM_VERSION.startswith(("2016.06", "2016.10", "2017.02"))
    ):
        assert isinstance(dut.sig_t4[3][4], LogicObject)
        assert isinstance(dut.sig_t4[3][4][1], LogicObject)
    assert isinstance(dut.sig_t5, ArrayObject)
    assert isinstance(dut.sig_t5[1], ArrayObject)
    assert isinstance(dut.sig_t5[1][0], LogicObject)
    assert isinstance(dut.sig_t5[1][0][6], LogicObject)
    assert isinstance(dut.sig_t6, ArrayObject)
    assert isinstance(dut.sig_t6[1], ArrayObject)
    # the following version cannot index into those arrays and will error out
    if not (
        LANGUAGE in ["verilog"]
        and cocotb.SIM_NAME.lower().startswith("riviera")
        and cocotb.SIM_VERSION.startswith(("2016.06", "2016.10", "2017.02"))
    ):
        assert isinstance(dut.sig_t6[0][3], LogicObject)
        assert isinstance(dut.sig_t6[0][3][7], LogicObject)
    assert isinstance(dut.sig_cmplx, ArrayObject)

    if LANGUAGE in ["verilog"]:
        assert isinstance(dut.sig_t7[1], ArrayObject)
        assert isinstance(dut.sig_t7[0][3], LogicObject)
        assert isinstance(
            dut.sig_t8[1], LogicObject
        )  # packed array of logic is mapped to GPI_NET
        assert isinstance(dut.sig_t8[0][3], LogicObject)

    # Riviera has a bug and finds dut.sig_cmplx[1], but the type returned is a vpiBitVar
    # only true for version 2016.02
    if not (
        LANGUAGE in ["verilog"]
        and cocotb.SIM_NAME.lower().startswith("riviera")
        and cocotb.SIM_VERSION.startswith("2016.02")
    ):
        assert isinstance(dut.sig_cmplx[1], HierarchyObject)
        assert isinstance(dut.sig_cmplx[1].a, LogicObject)
        assert isinstance(dut.sig_cmplx[1].b, ArrayObject)
        assert isinstance(dut.sig_cmplx[1].b[1], LogicObject)
        assert isinstance(dut.sig_cmplx[1].b[1][2], LogicObject)

    assert isinstance(dut.sig_rec, HierarchyObject)
    assert isinstance(dut.sig_rec.a, LogicObject)
    assert isinstance(dut.sig_rec.b, ArrayObject)

    # Riviera has a bug and finds dut.sig_rec.b[1], but the type returned is 0 which is unknown
    # only true for version 2016.02
    if not (
        LANGUAGE in ["verilog"]
        and cocotb.SIM_NAME.lower().startswith("riviera")
        and cocotb.SIM_VERSION.startswith("2016.02")
    ):
        assert isinstance(dut.sig_rec.b[1], LogicObject)
        assert isinstance(dut.sig_rec.b[1][2], LogicObject)


@cocotb.test(skip=(LANGUAGE in ["verilog"]))
async def test_extended_identifiers(dut):
    """Test accessing extended identifiers"""

    assert isinstance(dut["\\ext_id\\"], LogicObject)
    assert isinstance(dut["\\!\\"], LogicObject)
