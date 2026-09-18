# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for SystemVerilog interfaces reached through references.

An interface passed through a module port is a reference (``vpiRefObj``), not
an interface in its own right. cocotb resolves such a reference to the
interface instance it refers to, so the resulting object is the concrete
interface: its path is the concrete path, and reading or writing its signals
acts on the interface instance itself.
"""

from __future__ import annotations

import cocotb
from cocotb.handle import ArrayObject, HierarchyArrayObject, HierarchyObject
from cocotb.triggers import Timer

SIM_NAME = cocotb.SIM_NAME.lower()

# Verilator does not implement vpiInterfaceArray, so an array of interface
# references is only visible as its individual elements and cocotb represents
# it as a pseudo-region. Simulators with real array support return an array
# object instead.
ref_array_is_pseudo_region = SIM_NAME.startswith("verilator")


@cocotb.test()
async def test_sv_if_ref_type(dut):
    """Test that an interface reference resolves to the interface itself"""
    assert isinstance(dut.sub_i.sv_if_ref, HierarchyObject)


@cocotb.test()
async def test_sv_if_ref_path(dut):
    """Test that an interface reference reports the concrete interface path"""
    assert dut.sub_i.sv_if_ref._path == "top.sv_if_i"


@cocotb.test()
async def test_sv_if_ref_is_concrete_object(dut):
    """Test that a reference and the direct path give the same object"""
    assert dut.sub_i.sv_if_ref is dut.sv_if_i


@cocotb.test()
async def test_sv_if_ref_signals(dut):
    """Test that signals inside a referenced interface are discovered"""
    assert {"a", "b", "c"} <= set(dut.sub_i.sv_if_ref._keys())


@cocotb.test()
async def test_sv_if_ref_signal_path(dut):
    """Test that signals reached through a reference report a concrete path"""
    assert dut.sub_i.sv_if_ref.a._path == "top.sv_if_i.a"


@cocotb.test()
async def test_sv_if_ref_read_write(dut):
    """Test reading and writing a signal through an interface reference"""
    # Write through the reference, read back through the direct path.
    dut.sub_i.sv_if_ref.a.value = 1
    await Timer(1, "step")
    assert dut.sv_if_i.a.value == 1

    # And the other way around.
    dut.sv_if_i.a.value = 0
    await Timer(1, "step")
    assert dut.sub_i.sv_if_ref.a.value == 0


@cocotb.test()
async def test_sv_if_modport_ref_type(dut):
    """Test that a modport reference resolves to the interface itself"""
    assert isinstance(dut.sub_i.sv_if_modport_ref, HierarchyObject)


@cocotb.test()
async def test_sv_if_modport_ref_path(dut):
    """Test that a modport reference reports the concrete interface path"""
    assert dut.sub_i.sv_if_modport_ref._path == "top.sv_if_i"
    assert dut.sub_i.sv_if_modport_ref is dut.sv_if_i


@cocotb.test()
async def test_sv_if_modport_ref_read_write(dut):
    """Test reading and writing a signal through a modport reference"""
    dut.sub_i.sv_if_modport_ref.a.value = 1
    await Timer(1, "step")
    assert dut.sv_if_i.a.value == 1

    dut.sub_i.sv_if_modport_ref.a.value = 0
    await Timer(1, "step")
    assert dut.sub_i.sv_if_modport_ref.a.value == 0


@cocotb.test()
async def test_sv_if_ref_arr_type(dut):
    """Test that an array of interface references is the correct type"""
    if ref_array_is_pseudo_region:
        assert isinstance(dut.sub_i.sv_if_ref_arr, HierarchyArrayObject)
    else:
        assert isinstance(dut.sub_i.sv_if_ref_arr, ArrayObject)


# The tests that discover the children of the array must run before any test
# that reaches an element by index, since indexing populates the same child
# cache that discovery fills and would mask a discovery failure.
#
# Discovery is broken for a pseudo-region standing in for an array of
# references: the elements are named after the concrete interface array
# (sv_if_arr[N]), but the pseudo-region is named after the port
# (sv_if_ref_arr), so HierarchyArrayObject._sub_handle_key cannot extract an
# index from them and drops every child. Indexing is unaffected because it
# looks elements up by index rather than by name.
@cocotb.test(expect_fail=ref_array_is_pseudo_region)
async def test_sv_if_ref_arr_len(dut):
    """Test that the length of an interface reference array is correct"""
    assert len(dut.sub_i.sv_if_ref_arr) == 3


@cocotb.test(expect_fail=ref_array_is_pseudo_region)
async def test_sv_if_ref_arr_iteration(dut):
    """Test that an array of interface references can be iterated"""
    paths = [elem._path for elem in dut.sub_i.sv_if_ref_arr]
    assert paths == [f"top.sv_if_arr[{i}]" for i in range(3)]


@cocotb.test()
async def test_sv_if_ref_arr_access(dut):
    """Test that elements of an interface reference array can be accessed"""
    for i in range(3):
        assert {"a", "b", "c"} <= set(dut.sub_i.sv_if_ref_arr[i]._keys())


@cocotb.test()
async def test_sv_if_ref_arr_path(dut):
    """Test that reference array elements report the concrete interface path"""
    for i in range(3):
        assert dut.sub_i.sv_if_ref_arr[i]._path == f"top.sv_if_arr[{i}]"
        assert dut.sub_i.sv_if_ref_arr[i] is dut.sv_if_arr[i]


@cocotb.test()
async def test_sv_if_ref_arr_signal_path(dut):
    """Test that signals in a reference array report a concrete path"""
    for i in range(3):
        assert dut.sub_i.sv_if_ref_arr[i].b._path == f"top.sv_if_arr[{i}].b"


@cocotb.test()
async def test_sv_if_ref_arr_read_write(dut):
    """Test reading and writing signals through an interface reference array"""
    for i in range(3):
        dut.sub_i.sv_if_ref_arr[i].b.value = 1
    await Timer(1, "step")
    for i in range(3):
        assert dut.sv_if_arr[i].b.value == 1

    for i in range(3):
        dut.sv_if_arr[i].b.value = 0
    await Timer(1, "step")
    for i in range(3):
        assert dut.sub_i.sv_if_ref_arr[i].b.value == 0
