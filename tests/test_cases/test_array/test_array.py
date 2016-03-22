"""
A set of tests that demonstrate Array structure support
"""

import cocotb
import logging

from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge
from cocotb.result import TestError, TestFailure
from cocotb.handle import HierarchyObject, HierarchyArrayObject, ModifiableObject, NonHierarchyIndexableObject, ConstantObject

def _check_type(tlog, hdl, expected):
    if not isinstance(hdl, expected):
        raise TestFailure(">{0} ({1})< should be >{2}<".format(hdl._fullname, type(hdl) ,expected))
    else:
        tlog.info("   Found %s (%s) with length=%d", hdl._fullname, type(hdl), len(hdl))

@cocotb.test()
def test_gen_loop(dut):
    """Test accessing Generate Loops"""
    tlog = logging.getLogger("cocotb.test")

    yield Timer(1000)

    asc_gen_20  = dut.asc_gen[20]
    desc_gen    = dut.desc_gen

    if not isinstance(dut.asc_gen, HierarchyArrayObject):
        raise TestFailure("Generate Loop parent >{}< should be HierarchyArrayObject".format(dut.asc_gen))

    if not isinstance(desc_gen, HierarchyArrayObject):
        raise TestFailure("Generate Loop parent >{}< should be HierarchyArrayObject".format(desc_gen))

    if not isinstance(asc_gen_20, HierarchyObject):
        raise TestFailure("Generate Loop child >{}< should be HierarchyObject".format(asc_gen_20))

    tlog.info("Direct access found %s", asc_gen_20)
    tlog.info("Direct access found %s", desc_gen)

    for gens in desc_gen:
        tlog.info("Iterate access found %s", gens)

    if len(desc_gen) != 8:
        raise TestError("Length of desc_gen is >%d< and should be 8".format(len(desc_gen)))
    else:
        tlog.info("Length of desc_gen is %d", len(desc_gen))

    if len(dut.asc_gen) != 8:
        raise TestError("Length of asc_gen is >%d< and should be 8".format(len(dut.asc_gen)))
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
                           5 (sig_t1)
                          37 (sig_t2[7:4][7:0])
                          37 (sig_t3a[1:4][7:0])
                          37 (sig_t3b[3:0][7:0])
                         149 (sig_t4[0:3][7:4][7:0])
                         112 (sig_t5[0:2][0:3][7:0])
                          57 (sig_t6[0:1][2:4][7:0])
                           1 (sig_logic)
                           9 (sig_logic_vec)
                           1 (sig_bool)                                              (VHDL Only)
                           1 (sig_int)                                               (VHDL Only)
                           1 (sig_real)                                              (VHDL Only)
                           1 (sig_char)                                              (VHDL Only)
                           9 (sig_str)                                               (VHDL Only)
                          30 (sig_rec.a, sig_rec.b[0:2][7:0])                        (VPI doesn't find, added manually, except for Aldec)
                          61 (sig_cmplx[0:1].a, sig_cmplx[0:1].b[0:2][7:0])          (VPI - Aldec doesn't find)
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

                  TOTAL: 854 (VHDL - Default)
                         816 (VHDL - Aldec)
                         780 (Verilog - Default)
                         649 (Verilog - Aldec)
    """

    tlog = logging.getLogger("cocotb.test")

    yield Timer(1000)

    # Need to clear sub_handles so won't attempt to iterate over handles like sig_rec and sig_rec_array
    #
    # DO NOT REMOVE.  Aldec cannot iterate over the complex records due to bugs in the VPI interface.
    if cocotb.LANGUAGE in ["verilog"] and cocotb.SIM_NAME.lower().startswith(("riviera")):
        if len(dut._sub_handles) != 0:
            dut._sub_handles = {}

    # Modelsim/Questa VPI will not find a vpiStructVar from vpiModule so we set a dummy variable
    # to ensure the handle is in the dut "sub_handles" for iterating
    #
    # DO NOT ADD FOR ALDEC.  Does not iterate over properly
    if cocotb.LANGUAGE in ["verilog"] and cocotb.SIM_NAME.lower().startswith(("modelsim","ncsim")):
        dummy = dut.sig_rec
        dummy = dut.port_rec_out

    # Riviera-Pro's VHPI implementation does not fine signal declarations when iterating
    if cocotb.LANGUAGE in ["vhdl"] and cocotb.SIM_NAME.lower().startswith(("riviera")):
        for hdl in dut.asc_gen:
            dummy = hdl.sig
        for hdl in dut.desc_gen:
            dummy = hdl.sig

    if cocotb.LANGUAGE in ["vhdl"] and cocotb.SIM_NAME.lower().startswith(("riviera")):
        pass_total = 816
    elif cocotb.LANGUAGE in ["vhdl"]:
        pass_total = 854
    elif cocotb.LANGUAGE in ["verilog"] and cocotb.SIM_NAME.lower().startswith(("riviera")):
        pass_total = 649
    else:
        pass_total = 780

    def _discover(obj,indent):
        count = 0
        new_indent = indent+"---"
        for thing in obj:
            count += 1
            tlog.info("%sFound %s (%s)", indent, thing._fullname, type(thing))
            count += _discover(thing,new_indent)
        return count

    tlog.info("Iterating over %s (%s)", dut._fullname, type(dut))
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
        raise TestFailure("Expected dut.desc_gen[2].sig to be a 1 but got {}".format(int(dut.desc_gen[2].sig)))
    else:
        tlog.info("   dut.desc_gen[2].sig = %d", int(dut.desc_gen[2].sig))

    if int(dut.asc_gen[18].sig) != 1:
        raise TestFailure("Expected dut.asc_gen[18].sig to be a 1 but got {}".format(int(dut.asc_gen[18].sig)))
    else:
        tlog.info("   dut.asc_gen[18].sig = %d", int(dut.asc_gen[18].sig))

    tlog.info("Checking indexing of data with offset index.")
    if int(dut.port_ofst_out) != 64:
        raise TestFailure("Expected dut.port_ofst_out to be a 64 but got {}".format(int(dut.port_ofst_out)))
    else:
        tlog.info("   dut.port_ofst_out = %d (%s)", int(dut.port_ofst_out), dut.port_ofst_out.value.binstr)

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
    _check_type(tlog, dut.sig_t4[3][4], ModifiableObject)
    _check_type(tlog, dut.sig_t4[3][4][1], ModifiableObject)
    _check_type(tlog, dut.sig_t5, NonHierarchyIndexableObject)
    _check_type(tlog, dut.sig_t5[1], NonHierarchyIndexableObject)
    _check_type(tlog, dut.sig_t5[1][0], ModifiableObject)
    _check_type(tlog, dut.sig_t5[1][0][6], ModifiableObject)
    _check_type(tlog, dut.sig_t6, NonHierarchyIndexableObject)
    _check_type(tlog, dut.sig_t6[1], NonHierarchyIndexableObject)
    _check_type(tlog, dut.sig_t6[0][3], ModifiableObject)
    _check_type(tlog, dut.sig_t6[0][3][7], ModifiableObject)
    _check_type(tlog, dut.sig_cmplx, NonHierarchyIndexableObject)

    # Riviera has a bug and finds dut.sig_cmplx[1], but the type returned is a vpiBitVar
    if not (cocotb.LANGUAGE in ["verilog"] and cocotb.SIM_NAME.lower().startswith(("riviera"))):
        _check_type(tlog, dut.sig_cmplx[1], HierarchyObject)
        _check_type(tlog, dut.sig_cmplx[1].a, ModifiableObject)
        _check_type(tlog, dut.sig_cmplx[1].b, NonHierarchyIndexableObject)
        _check_type(tlog, dut.sig_cmplx[1].b[1], ModifiableObject)
        _check_type(tlog, dut.sig_cmplx[1].b[1][2], ModifiableObject)
        tlog.info("   dut.sig_cmplx[1].a = %d (%s)", int(dut.sig_cmplx[1].a), dut.sig_cmplx[1].a.value.binstr)

    _check_type(tlog, dut.sig_rec, HierarchyObject)
    _check_type(tlog, dut.sig_rec.a, ModifiableObject)
    _check_type(tlog, dut.sig_rec.b, NonHierarchyIndexableObject)

    # Riviera has a bug and finds dut.sig_rec.b[1], but the type returned is 0 which is unknown
    if not (cocotb.LANGUAGE in ["verilog"] and cocotb.SIM_NAME.lower().startswith(("riviera"))):
        _check_type(tlog, dut.sig_rec.b[1], ModifiableObject)
        _check_type(tlog, dut.sig_rec.b[1][2], ModifiableObject)

