"""
A set of tests that demonstrate Array structure support
"""

import logging
import cocotb

from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge
from cocotb.result import TestError, TestFailure
from cocotb.handle import HierarchyObject, HierarchyArrayObject, ModifiableObject, NonHierarchyIndexableObject, ConstantObject

def _check_type(tlog, hdl, expected):
    if not isinstance(hdl, expected):
        raise TestFailure(">{0!r} ({1})< should be >{2}<".format(hdl, hdl._type, expected))
    else:
        tlog.info("   Found %r (%s) with length=%d", hdl, hdl._type, len(hdl))

def _check_int(tlog, hdl, expected):
    if int(hdl) != expected:
        raise TestFailure("{2!r}: Expected >{0}< but got >{1}<".format(expected, int(hdl), hdl))
    else:
        tlog.info("   Found {0!r} ({1}) with value={2}".format(hdl, hdl._type, int(hdl)))

def _check_logic(tlog, hdl, expected):
    if int(hdl) != expected:
        raise TestFailure("{2!r}: Expected >0x{0:X}< but got >0x{1:X}<".format(expected, int(hdl), hdl))
    else:
        tlog.info("   Found {0!r} ({1}) with value=0x{2:X}".format(hdl, hdl._type, int(hdl)))

def _check_str(tlog, hdl, expected):
    if str(hdl) != expected:
        raise TestFailure("{2!r}: Expected >{0}< but got >{1}<".format(expected, str(hdl), hdl))
    else:
        tlog.info("   Found {0!r} ({1}) with value={2}".format(hdl, hdl._type, str(hdl)))

def _check_real(tlog, hdl, expected):
    if float(hdl) != expected:
        raise TestFailure("{2!r}: Expected >{0}< but got >{1}<".format(expected, float(hdl), hdl))
    else:
        tlog.info("   Found {0!r} ({1}) with value={2}".format(hdl, hdl._type, float(hdl)))

@cocotb.test()
def test_read_write(dut):
    """Test handle inheritance"""
    tlog = logging.getLogger("cocotb.test")

    cocotb.fork(Clock(dut.clk, 1000).start())

    yield Timer(1000)

    tlog.info("Checking Generics/Parameters:")
    _check_logic(tlog, dut.param_logic    , 1)
    _check_logic(tlog, dut.param_logic_vec, 0xDA)

    if cocotb.LANGUAGE in ["vhdl"]:
        _check_int (tlog, dut.param_bool, 1)
        _check_int (tlog, dut.param_int , 6)
        _check_real(tlog, dut.param_real, 3.14)
        _check_int (tlog, dut.param_char, ord('p'))
        _check_str (tlog, dut.param_str , "ARRAYMOD")

        if not cocotb.SIM_NAME.lower().startswith(("riviera")):
            _check_logic(tlog, dut.param_rec.a        , 0)
            _check_logic(tlog, dut.param_rec.b[0]     , 0)
            _check_logic(tlog, dut.param_rec.b[1]     , 0)
            _check_logic(tlog, dut.param_rec.b[2]     , 0)
            _check_logic(tlog, dut.param_cmplx[0].a   , 0)
            _check_logic(tlog, dut.param_cmplx[0].b[0], 0)
            _check_logic(tlog, dut.param_cmplx[0].b[1], 0)
            _check_logic(tlog, dut.param_cmplx[0].b[2], 0)
            _check_logic(tlog, dut.param_cmplx[1].a   , 0)
            _check_logic(tlog, dut.param_cmplx[1].b[0], 0)
            _check_logic(tlog, dut.param_cmplx[1].b[1], 0)
            _check_logic(tlog, dut.param_cmplx[1].b[2], 0)

    tlog.info("Checking Constants:")
    _check_logic(tlog, dut.const_logic    , 0)
    _check_logic(tlog, dut.const_logic_vec, 0x3D)

    if cocotb.LANGUAGE in ["vhdl"]:
        _check_int (tlog, dut.const_bool, 0)
        _check_int (tlog, dut.const_int , 12)
        _check_real(tlog, dut.const_real, 6.28)
        _check_int (tlog, dut.const_char, ord('c'))
        _check_str (tlog, dut.const_str , "MODARRAY")

        if not cocotb.SIM_NAME.lower().startswith(("riviera")):
            _check_logic(tlog, dut.const_rec.a        , 1)
            _check_logic(tlog, dut.const_rec.b[0]     , 0xFF)
            _check_logic(tlog, dut.const_rec.b[1]     , 0xFF)
            _check_logic(tlog, dut.const_rec.b[2]     , 0xFF)
            _check_logic(tlog, dut.const_cmplx[1].a   , 1)
            _check_logic(tlog, dut.const_cmplx[1].b[0], 0xFF)
            _check_logic(tlog, dut.const_cmplx[1].b[1], 0xFF)
            _check_logic(tlog, dut.const_cmplx[1].b[2], 0xFF)
            _check_logic(tlog, dut.const_cmplx[2].a   , 1)
            _check_logic(tlog, dut.const_cmplx[2].b[0], 0xFF)
            _check_logic(tlog, dut.const_cmplx[2].b[1], 0xFF)
            _check_logic(tlog, dut.const_cmplx[2].b[2], 0xFF)

    dut.select_in         = 2

    yield Timer(1000)

    tlog.info("Writing the signals!!!")
    dut.sig_logic         = 1
    dut.sig_logic_vec     = 0xCC
    if cocotb.LANGUAGE in ["vhdl"]:
        dut.sig_bool          = 1
        dut.sig_int           = 5000
        dut.sig_real          = 22.54
        dut.sig_char          = ord('Z')
        dut.sig_str           = "Testing"
        dut.sig_rec.a         = 1
        dut.sig_rec.b[0]      = 0x01
        dut.sig_rec.b[1]      = 0x23
        dut.sig_rec.b[2]      = 0x45
        dut.sig_cmplx[0].a    = 0
        dut.sig_cmplx[0].b[0] = 0x67
        dut.sig_cmplx[0].b[1] = 0x89
        dut.sig_cmplx[0].b[2] = 0xAB
        dut.sig_cmplx[1].a    = 1
        dut.sig_cmplx[1].b[0] = 0xCD
        dut.sig_cmplx[1].b[1] = 0xEF
        dut.sig_cmplx[1].b[2] = 0x55

    yield Timer(1000)

    tlog.info("Checking writes:")
    _check_logic(tlog, dut.port_logic_out    , 1)
    _check_logic(tlog, dut.port_logic_vec_out, 0xCC)

    if cocotb.LANGUAGE in ["vhdl"]:
        _check_int (tlog, dut.port_bool_out, 1)
        _check_int (tlog, dut.port_int_out , 5000)
        _check_real(tlog, dut.port_real_out, 22.54)
        _check_int (tlog, dut.port_char_out, ord('Z'))
        _check_str (tlog, dut.port_str_out , "Testing")

        _check_logic(tlog, dut.port_rec_out.a        , 1)
        _check_logic(tlog, dut.port_rec_out.b[0]     , 0x01)
        _check_logic(tlog, dut.port_rec_out.b[1]     , 0x23)
        _check_logic(tlog, dut.port_rec_out.b[2]     , 0x45)
        _check_logic(tlog, dut.port_cmplx_out[0].a   , 0)
        _check_logic(tlog, dut.port_cmplx_out[0].b[0], 0x67)
        _check_logic(tlog, dut.port_cmplx_out[0].b[1], 0x89)
        _check_logic(tlog, dut.port_cmplx_out[0].b[2], 0xAB)
        _check_logic(tlog, dut.port_cmplx_out[1].a   , 1)
        _check_logic(tlog, dut.port_cmplx_out[1].b[0], 0xCD)
        _check_logic(tlog, dut.port_cmplx_out[1].b[1], 0xEF)
        _check_logic(tlog, dut.port_cmplx_out[1].b[2], 0x55)

    tlog.info("Writing a few signal sub-indices!!!")
    dut.sig_logic_vec[2]     = 0
    if cocotb.LANGUAGE in ["vhdl"] or not (cocotb.SIM_NAME.lower().startswith(("ncsim", "xmsim")) or
                                           (cocotb.SIM_NAME.lower().startswith(("riviera")) and
                                            cocotb.SIM_VERSION.startswith(("2016.06", "2016.10", "2017.02")))):
        dut.sig_t6[1][3][2]      = 1
        dut.sig_t6[0][2][7]      = 0

    if cocotb.LANGUAGE in ["vhdl"]:
        dut.sig_str[2]           = ord('E')
        dut.sig_rec.b[1][7]      = 1
        dut.sig_cmplx[1].b[1][0] = 0

    yield Timer(1000)

    tlog.info("Checking writes (2):")
    _check_logic(tlog, dut.port_logic_vec_out, 0xC8)
    if cocotb.LANGUAGE in ["vhdl"] or not (cocotb.SIM_NAME.lower().startswith(("ncsim", "xmsim")) or
                                           (cocotb.SIM_NAME.lower().startswith(("riviera")) and
                                            cocotb.SIM_VERSION.startswith(("2016.06", "2016.10", "2017.02")))):
        _check_logic(tlog, dut.sig_t6[1][3][2], 1)
        _check_logic(tlog, dut.sig_t6[0][2][7], 0)

    if cocotb.LANGUAGE in ["vhdl"]:
        _check_str(tlog, dut.port_str_out, "Testing")

        _check_logic(tlog, dut.port_rec_out.b[1]     , 0xA3)
        _check_logic(tlog, dut.port_cmplx_out[1].b[1], 0xEE)

@cocotb.test()
def test_gen_loop(dut):
    """Test accessing Generate Loops"""
    tlog = logging.getLogger("cocotb.test")

    yield Timer(1000)

    asc_gen_20  = dut.asc_gen[20]
    desc_gen    = dut.desc_gen

    if not isinstance(dut.asc_gen, HierarchyArrayObject):
        raise TestFailure("Generate Loop parent >{!r}< should be HierarchyArrayObject".format(dut.asc_gen))

    if not isinstance(desc_gen, HierarchyArrayObject):
        raise TestFailure("Generate Loop parent >{!r}< should be HierarchyArrayObject".format(desc_gen))

    if not isinstance(asc_gen_20, HierarchyObject):
        raise TestFailure("Generate Loop child >{!r}< should be HierarchyObject".format(asc_gen_20))

    tlog.info("Direct access found %s", asc_gen_20)
    tlog.info("Direct access found %s", desc_gen)

    for gens in desc_gen:
        tlog.info("Iterate access found %s", gens)

    if len(desc_gen) != 8:
        raise TestError("Length of desc_gen is >{}< and should be 8".format(len(desc_gen)))
    else:
        tlog.info("Length of desc_gen is %d", len(desc_gen))

    if len(dut.asc_gen) != 8:
        raise TestError("Length of asc_gen is >{}< and should be 8".format(len(dut.asc_gen)))
    else:
        tlog.info("Length of asc_gen is %d", len(dut.asc_gen))

    for gens in dut.asc_gen:
        tlog.info("Iterate access found %s", gens)

@cocotb.test()
def test_discover_all(dut):
    """Discover everything in the DUT:
          dut
                 TYPE    CNT  NOTES                                                  EXCEPTIONS
             parameters: 7/2 (base types)                                            (VHDL/Verilog)
                           6 (param_rec.a, param_rec.b[0:2])                         (VHDL only excluding Aldec)
                          13 (param_cmplx[0:1].a, param_cmplx[0:1].b[0:2])           (VHDL only excluding Aldec)
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
                           1 (const_logic_vec)
                           1 (const_bool)                                            (VHDL Only)
                           1 (const_int)                                             (VHDL Only)
                           1 (const_real)                                            (VHDL Only)
                           1 (const_char)                                            (VHDL Only)
                           1 (const_str)                                             (VHDL Only)
                           6 (const_rec.a, const_rec.b[0:2])                         (VHDL only excluding Aldec)
                          13 (const_cmplx[1:2].a, const_cmplx[1:2].b[0:2])           (VHDL only excluding Aldec)
                signals:   9 (sig_desc)
                           9 (sig_asc)
                           1 (\ext_id\)                                              (VHDL only)
                           1 (\!\)                                                   (VHDL only)
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
                           8 (asc_gen: signals)                                      (VHPI - Riviera doesn't find, added manually)
                           8 (asc_gen: constant)
                           8 (asc_gen: variable)
                           8 (asc_gen: process "always")                             (VPI - Aldec only)
                           9 (desc_gen[7:0])
                           8 (desc_gen: signals)                                     (VHPI - Riviera doesn't find, added manually)
                           8 (desc_gen: constant)
                           8 (desc_gen: variable)
                           8 (desc_gen: process "always")                            (VPI - Aldec only)
                process:   1 ("always")                                              (VPI - Aldec only)

                  TOTAL:  856 (VHDL - Default)
                          818 (VHDL - Aldec)
                         1078 (Verilog - Default)
                     947/1038 (Verilog - Aldec)
    """

    tlog = logging.getLogger("cocotb.test")

    yield Timer(1000)

    # Need to clear sub_handles so won't attempt to iterate over handles like sig_rec and sig_rec_array
    #
    # DO NOT REMOVE.  Aldec cannot iterate over the complex records due to bugs in the VPI interface.
    if (cocotb.LANGUAGE in ["verilog"] and cocotb.SIM_NAME.lower().startswith(("riviera")) and
        cocotb.SIM_VERSION.startswith(("2016.02"))) :
        if len(dut._sub_handles) != 0:
            dut._sub_handles = {}

    # Modelsim/Questa VPI will not find a vpiStructVar from vpiModule so we set a dummy variable
    # to ensure the handle is in the dut "sub_handles" for iterating
    #
    # DO NOT ADD FOR ALDEC.  Does not iterate over properly
    if cocotb.LANGUAGE in ["verilog"] and cocotb.SIM_NAME.lower().startswith(("modelsim", "ncsim", "xmsim")):
        dummy = dut.sig_rec
        dummy = dut.port_rec_out

    # Riviera-Pro's VHPI implementation does not fine signal declarations when iterating
    if cocotb.LANGUAGE in ["vhdl"] and cocotb.SIM_NAME.lower().startswith(("riviera")):
        for hdl in dut.asc_gen:
            dummy = hdl.sig
        for hdl in dut.desc_gen:
            dummy = hdl.sig

    if cocotb.LANGUAGE in ["vhdl"] and cocotb.SIM_NAME.lower().startswith(("riviera")):
        pass_total = 818
    elif cocotb.LANGUAGE in ["vhdl"]:
        pass_total = 856
    elif cocotb.LANGUAGE in ["verilog"] and cocotb.SIM_NAME.lower().startswith(("riviera")):
        if cocotb.SIM_VERSION.startswith(("2017.10.61")):
            pass_total = 803
        elif cocotb.SIM_VERSION.startswith(("2016.06", "2016.10", "2017.02")):
            pass_total = 813
        elif cocotb.SIM_VERSION.startswith(("2016.02")):
            pass_total = 947
        else:
            pass_total = 1038
    else:
        pass_total = 1078

    def _discover(obj, indent):
        count = 0
        new_indent = indent+"---"
        for thing in obj:
            count += 1
            tlog.info("%sFound %r (%s)", indent, thing, thing._type)
            count += _discover(thing, new_indent)
        return count

    tlog.info("Iterating over %r (%s)", dut, dut._type)
    total = _discover(dut, "")
    tlog.info("Found a total of %d things", total)
    if total != pass_total:
        raise TestFailure("Expected {0} objects but found {1}".format(pass_total, total))

@cocotb.test(skip=(cocotb.LANGUAGE in ["verilog"] or cocotb.SIM_NAME.lower().startswith(("riviera"))))
def test_direct_constant_indexing(dut):
    """Test directly accessing constant/parameter data in arrays, i.e. not iterating"""

    tlog = logging.getLogger("cocotb.test")

    yield Timer(2000)

    tlog.info("Checking Types of complex array structures in constants/parameters.")
    _check_type(tlog, dut.param_rec, HierarchyObject)
    _check_type(tlog, dut.param_rec.a, ConstantObject)
    _check_type(tlog, dut.param_rec.b, NonHierarchyIndexableObject)
    _check_type(tlog, dut.param_rec.b[1], ConstantObject)

    _check_type(tlog, dut.param_cmplx, NonHierarchyIndexableObject)
    _check_type(tlog, dut.param_cmplx[0], HierarchyObject)
    _check_type(tlog, dut.param_cmplx[0].a, ConstantObject)
    _check_type(tlog, dut.param_cmplx[0].b, NonHierarchyIndexableObject)
    _check_type(tlog, dut.param_cmplx[0].b[1], ConstantObject)

    _check_type(tlog, dut.const_rec, HierarchyObject)
    _check_type(tlog, dut.const_rec.a, ConstantObject)
    _check_type(tlog, dut.const_rec.b, NonHierarchyIndexableObject)
    _check_type(tlog, dut.const_rec.b[1], ConstantObject)

    _check_type(tlog, dut.const_cmplx, NonHierarchyIndexableObject)
    _check_type(tlog, dut.const_cmplx[1], HierarchyObject)
    _check_type(tlog, dut.const_cmplx[1].a, ConstantObject)
    _check_type(tlog, dut.const_cmplx[1].b, NonHierarchyIndexableObject)
    _check_type(tlog, dut.const_cmplx[1].b[1], ConstantObject)


@cocotb.test()
def test_direct_signal_indexing(dut):
    """Test directly accessing signal/net data in arrays, i.e. not iterating"""

    tlog = logging.getLogger("cocotb.test")

    cocotb.fork(Clock(dut.clk, 1000).start())

    dut.port_desc_in <= 0
    dut.port_asc_in  <= 0
    dut.port_ofst_in <= 0

    yield Timer(2000)

    dut.port_desc_in[2] <= 1
    dut.port_asc_in[2]  <= 1
    dut.port_ofst_in[2] <= 1

    yield Timer(2000)

    tlog.info("Checking bit mapping from input to generate loops.")
    if int(dut.desc_gen[2].sig) != 1:
        raise TestFailure("Expected {0!r} to be a 1 but got {1}".format(dut.desc_gen[2].sig, int(dut.desc_gen[2].sig)))
    else:
        tlog.info("   %r = %d", dut.desc_gen[2].sig, int(dut.desc_gen[2].sig))

    if int(dut.asc_gen[18].sig) != 1:
        raise TestFailure("Expected {0!r} to be a 1 but got {1}".format(dut.asc_gen[18].sig, int(dut.asc_gen[18].sig)))
    else:
        tlog.info("   %r = %d", dut.asc_gen[18].sig, int(dut.asc_gen[18].sig))

    tlog.info("Checking indexing of data with offset index.")
    if int(dut.port_ofst_out) != 64:
        raise TestFailure("Expected {0!r} to be a 64 but got {1}".format(dut.port_ofst_out, int(dut.port_ofst_out)))
    else:
        tlog.info("   %r = %d (%s)", dut.port_ofst_out, int(dut.port_ofst_out), dut.port_ofst_out.value.binstr)

    tlog.info("Checking Types of complex array structures in signals.")
    _check_type(tlog, dut.sig_desc[20], ModifiableObject)
    _check_type(tlog, dut.sig_asc[17], ModifiableObject)
    _check_type(tlog, dut.sig_t1, ModifiableObject)
    _check_type(tlog, dut.sig_t2, NonHierarchyIndexableObject)
    _check_type(tlog, dut.sig_t2[5], ModifiableObject)
    _check_type(tlog, dut.sig_t2[5][3], ModifiableObject)
    _check_type(tlog, dut.sig_t3a[2][3], ModifiableObject)
    _check_type(tlog, dut.sig_t3b[3], ModifiableObject)
    _check_type(tlog, dut.sig_t3a, NonHierarchyIndexableObject)
    _check_type(tlog, dut.sig_t4, NonHierarchyIndexableObject)
    _check_type(tlog, dut.sig_t4[3], NonHierarchyIndexableObject)
    # the following version cannot index into those arrays and will error out
    if not (cocotb.LANGUAGE in ["verilog"] and cocotb.SIM_NAME.lower().startswith(("riviera")) and
            cocotb.SIM_VERSION.startswith(("2016.06", "2016.10", "2017.02"))):
        _check_type(tlog, dut.sig_t4[3][4], ModifiableObject)
        _check_type(tlog, dut.sig_t4[3][4][1], ModifiableObject)
    _check_type(tlog, dut.sig_t5, NonHierarchyIndexableObject)
    _check_type(tlog, dut.sig_t5[1], NonHierarchyIndexableObject)
    _check_type(tlog, dut.sig_t5[1][0], ModifiableObject)
    _check_type(tlog, dut.sig_t5[1][0][6], ModifiableObject)
    _check_type(tlog, dut.sig_t6, NonHierarchyIndexableObject)
    _check_type(tlog, dut.sig_t6[1], NonHierarchyIndexableObject)
    # the following version cannot index into those arrays and will error out
    if not (cocotb.LANGUAGE in ["verilog"] and cocotb.SIM_NAME.lower().startswith(("riviera")) and
            cocotb.SIM_VERSION.startswith(("2016.06", "2016.10", "2017.02"))):
        _check_type(tlog, dut.sig_t6[0][3], ModifiableObject)
        _check_type(tlog, dut.sig_t6[0][3][7], ModifiableObject)
    _check_type(tlog, dut.sig_cmplx, NonHierarchyIndexableObject)

    if cocotb.LANGUAGE in ["verilog"]:
        _check_type(tlog, dut.sig_t7[1], NonHierarchyIndexableObject)
        _check_type(tlog, dut.sig_t7[0][3], ModifiableObject)
        _check_type(tlog, dut.sig_t8[1], NonHierarchyIndexableObject)
        _check_type(tlog, dut.sig_t8[0][3], ModifiableObject)


    # Riviera has a bug and finds dut.sig_cmplx[1], but the type returned is a vpiBitVar
    # only true for version 2016.02
    if not (cocotb.LANGUAGE in ["verilog"] and cocotb.SIM_NAME.lower().startswith(("riviera")) and
            cocotb.SIM_VERSION.startswith(("2016.02"))):

        _check_type(tlog, dut.sig_cmplx[1], HierarchyObject)
        _check_type(tlog, dut.sig_cmplx[1].a, ModifiableObject)
        _check_type(tlog, dut.sig_cmplx[1].b, NonHierarchyIndexableObject)
        _check_type(tlog, dut.sig_cmplx[1].b[1], ModifiableObject)
        _check_type(tlog, dut.sig_cmplx[1].b[1][2], ModifiableObject)

    _check_type(tlog, dut.sig_rec, HierarchyObject)
    _check_type(tlog, dut.sig_rec.a, ModifiableObject)
    _check_type(tlog, dut.sig_rec.b, NonHierarchyIndexableObject)

    # Riviera has a bug and finds dut.sig_rec.b[1], but the type returned is 0 which is unknown
    # only true for version 2016.02
    if not (cocotb.LANGUAGE in ["verilog"] and cocotb.SIM_NAME.lower().startswith(("riviera")) and
            cocotb.SIM_VERSION.startswith(("2016.02"))):
        _check_type(tlog, dut.sig_rec.b[1], ModifiableObject)
        _check_type(tlog, dut.sig_rec.b[1][2], ModifiableObject)

@cocotb.test(skip=(cocotb.LANGUAGE in ["verilog"]))
def test_extended_identifiers(dut):
    """Test accessing extended identifiers"""

    tlog = logging.getLogger("cocotb.test")

    yield Timer(2000)

    tlog.info("Checking extended identifiers.")
    _check_type(tlog, dut._id("\\ext_id\\", extended=False), ModifiableObject)
    _check_type(tlog, dut._id("!"), ModifiableObject)
