# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for SystemVerilog interfaces reached through references."""

from __future__ import annotations

import cocotb
from cocotb.handle import HierarchyArrayObject, HierarchyObject, _make_sim_object
from cocotb.triggers import Combine, RisingEdge, Timer, with_timeout
from cocotb.types import Range
from cocotb_tools.sim_versions import VerilatorVersion

SIM_NAME = cocotb.SIM_NAME.lower()

xfail_without_if_refs = cocotb.xfail(
    SIM_NAME.startswith("verilator")
    and VerilatorVersion(cocotb.SIM_VERSION) < VerilatorVersion("5.053"),
    raises=AttributeError,
    reason="Verilator does not expose resolvable interface references before v5.053",
)


@xfail_without_if_refs
@cocotb.test()
async def test_sv_if_ref_signals(dut):
    """Test that signals inside a referenced interface are discovered"""
    assert {"a", "b", "c"} <= set(dut.sub_i.sv_if_ref_scalar_to_scalar._keys())


@xfail_without_if_refs
@cocotb.test()
async def test_sv_if_ref_signal_path(dut):
    """Test that a signal retains its reference path and exposes its target"""
    signal = dut.sub_i.sv_if_ref_scalar_to_scalar.a
    assert signal._name == "a"
    assert signal._path == "top.sub_i.sv_if_ref_scalar_to_scalar.a"
    actual = signal._handle.get_actual()
    assert actual is not None
    assert actual.get_name_string() == "a"
    assert actual.get_fullname_string() == "top.sv_if_i.a"
    # Resolve before accessing the target directly to exercise cache identity.
    actual_signal = _make_sim_object(actual, actual.get_fullname_string())
    assert actual_signal is dut.sv_if_i.a
    assert signal is not dut.sv_if_i.a
    assert actual.get_actual() is None


@xfail_without_if_refs
@cocotb.test()
async def test_sv_if_ref_read_write(dut):
    """Test reading and writing a signal through an interface reference"""
    dut.sub_i.sv_if_ref_scalar_to_scalar.a.value = 1
    await Timer(1, "step")
    assert dut.sv_if_i.a.value == 1

    dut.sv_if_i.a.value = 0
    await Timer(1, "step")
    assert dut.sub_i.sv_if_ref_scalar_to_scalar.a.value == 0


@xfail_without_if_refs
@cocotb.test()
async def test_sv_if_modport_ref_type(dut):
    """Test that a modport reference resolves to the interface itself"""
    assert isinstance(dut.sub_i.sv_if_modport_ref_scalar_to_scalar, HierarchyObject)


@xfail_without_if_refs
@cocotb.test()
async def test_sv_if_modport_ref_path(dut):
    """Test that a modport reference retains its name and path"""
    handle = dut.sub_i.sv_if_modport_ref_scalar_to_scalar
    assert handle._name == "sv_if_modport_ref_scalar_to_scalar"
    assert handle._path == "top.sub_i.sv_if_modport_ref_scalar_to_scalar"
    assert handle._handle.get_actual() == dut.sv_if_i._handle
    assert handle is not dut.sv_if_i


@xfail_without_if_refs
@cocotb.test()
async def test_sv_if_modport_ref_read_write(dut):
    """Test reading and writing a signal through a modport reference"""
    dut.sub_i.sv_if_modport_ref_scalar_to_scalar.a.value = 1
    await Timer(1, "step")
    assert dut.sv_if_i.a.value == 1

    dut.sub_i.sv_if_modport_ref_scalar_to_scalar.a.value = 0
    await Timer(1, "step")
    assert dut.sub_i.sv_if_modport_ref_scalar_to_scalar.a.value == 0


@xfail_without_if_refs
@cocotb.test()
async def test_sv_if_ref_arr_type(dut):
    """Test that an array of interface references is the correct type"""
    handle = dut.sub_i.sv_if_ref_size_to_size
    assert isinstance(handle, HierarchyArrayObject)
    assert handle._name == "sv_if_ref_size_to_size"
    assert handle._path == "top.sub_i.sv_if_ref_size_to_size"


# Discover these arrays before indexing so cached children cannot mask failures.
@xfail_without_if_refs
@cocotb.test()
async def test_sv_if_ref_arr_len(dut):
    """Test that the length of an interface reference array is correct"""
    assert len(dut.sub_i.sv_if_ref_size_to_size) == 3


@xfail_without_if_refs
@cocotb.test()
async def test_sv_if_ref_arr_iteration(dut):
    """Test that an array of interface references can be iterated"""
    paths = [elem._path for elem in dut.sub_i.sv_if_ref_size_to_size]
    assert paths == [f"top.sub_i.sv_if_ref_size_to_size[{i}]" for i in range(3)]


@xfail_without_if_refs
@cocotb.test()
async def test_sv_if_ref_arr_discovery(dut):
    """Test initial discovery of the alternate array and its reference targets"""
    handle = dut.sub_i.sv_if_ref_size_to_size_alt
    assert not handle._discovered, "Array was already discovered"
    elems = list(handle)

    assert len(handle) == 2
    assert [elem._path for elem in elems] == [
        f"top.sub_i.sv_if_ref_size_to_size_alt[{i}]" for i in range(2)
    ]
    assert [elem._handle.get_actual() for elem in elems] == [
        dut.unrelated_name_arr_size[i]._handle for i in range(2)
    ]


# Targets listed by ascending numerical port index.
# Connections map left-to-left in declaration order; see top.sv.
# Slice direction must match the source array.
ARRAY_PORT_TARGETS = {
    "sv_if_ref_size_to_size": [("sv_if_arr_size", i) for i in (0, 1, 2)],
    "sv_if_ref_size_to_size_alt": [("unrelated_name_arr_size", i) for i in (0, 1)],
    "sv_if_ref_size_to_dn": [("sv_if_arr_dn", i) for i in (2, 1, 0)],
    "sv_if_ref_size_to_size_slice": [("sv_if_arr_size", i) for i in (1, 2)],
    "sv_if_ref_size_to_dn_slice": [("sv_if_arr_dn", i) for i in (2, 1)],
    "sv_if_ref_size_to_size_one_slice": [("sv_if_arr_size", 2)],
    "sv_if_ref_size_to_dn_one_slice": [("sv_if_arr_dn", 1)],
    "sv_if_ref_up_to_size": [("sv_if_arr_size", i) for i in (0, 1, 2)],
    "sv_if_ref_up_to_dn": [("sv_if_arr_dn", i) for i in (2, 1, 0)],
    "sv_if_ref_dn_to_size": [("sv_if_arr_size", i) for i in (2, 1, 0)],
    "sv_if_ref_dn_to_dn": [("sv_if_arr_dn", i) for i in (0, 1, 2)],
    "sv_if_ref_offset_up_to_size": [("sv_if_arr_size", i) for i in (0, 1, 2)],
    "sv_if_ref_offset_dn_to_dn": [("sv_if_arr_dn", i) for i in (0, 1, 2)],
    "sv_if_ref_far_up_to_size": [("sv_if_arr_size", i) for i in (0, 1, 2)],
    "sv_if_ref_neg_up_to_size": [("sv_if_arr_size", i) for i in (0, 1, 2)],
    "sv_if_ref_allneg_up_to_dn": [("sv_if_arr_dn", i) for i in (2, 1, 0)],
    "sv_if_ref_size_to_up": [("sv_if_arr_up", i) for i in (0, 1, 2)],
    "sv_if_ref_up_to_up": [("sv_if_arr_up", i) for i in (0, 1, 2)],
    "sv_if_ref_dn_to_up": [("sv_if_arr_up", i) for i in (2, 1, 0)],
    "sv_if_ref_offset_up_to_up": [("sv_if_arr_up", i) for i in (0, 1, 2)],
    "sv_if_ref_neg_up_to_up": [("sv_if_arr_up", i) for i in (0, 1, 2)],
    "sv_if_modport_ref_dn_to_up": [("sv_if_arr_up", i) for i in (2, 1, 0)],
}

# Nondefault port bounds; omitted entries use [0:n-1].
ARRAY_PORT_RANGES = {
    "sv_if_ref_dn_to_size": (2, 0),
    "sv_if_ref_dn_to_dn": (2, 0),
    "sv_if_ref_offset_up_to_size": (1, 3),
    "sv_if_ref_offset_dn_to_dn": (3, 1),
    "sv_if_ref_far_up_to_size": (100, 102),
    "sv_if_ref_neg_up_to_size": (-1, 1),
    "sv_if_ref_allneg_up_to_dn": (-3, -1),
    "sv_if_ref_dn_to_up": (2, 0),
    "sv_if_ref_offset_up_to_up": (1, 3),
    "sv_if_ref_neg_up_to_up": (-1, 1),
    "sv_if_modport_ref_dn_to_up": (2, 0),
}

SCALAR_PORT_TARGETS = {
    "sv_if_ref_scalar_to_scalar": ("sv_if_i", None),
    "sv_if_ref_scalar_to_size": ("sv_if_arr_size", 1),
    "sv_if_ref_scalar_to_dn": ("sv_if_arr_dn", 1),
    "sv_if_ref_scalar_to_up": ("sv_if_arr_up", 1),
    "sv_if_modport_ref_scalar_to_up": ("sv_if_arr_up", 2),
}


def _target(dut, target_name, target_index):
    handle = getattr(dut, target_name)
    return handle if target_index is None else handle[target_index]


def _target_path(target_name, target_index):
    return target_name if target_index is None else f"{target_name}[{target_index}]"


def _port_indices(port):
    """Return the indices of an array port, in ascending order."""
    left, right = ARRAY_PORT_RANGES.get(port, (0, len(ARRAY_PORT_TARGETS[port]) - 1))
    return range(min(left, right), max(left, right) + 1)


@xfail_without_if_refs
@cocotb.test()
async def test_sv_if_ref_port_index_is_positional(dut):
    """Test that every array port maps its indices to the right interfaces"""
    for port, targets in ARRAY_PORT_TARGETS.items():
        handle = getattr(dut.sub_i, port)
        # A cached element must not suppress discovery of the remaining elements.
        first_index = min(_port_indices(port))
        first = handle[first_index]
        assert len(handle) == len(targets), port
        assert handle[first_index] is first, port
        assert handle._name == port
        assert handle._path == f"top.sub_i.{port}"
        for port_index, (target_name, target_index) in zip(
            _port_indices(port), targets
        ):
            elem = handle[port_index]
            assert elem._name == f"{port}[{port_index}]"
            assert elem._path == f"top.sub_i.{port}[{port_index}]"
            target = _target(dut, target_name, target_index)
            assert elem._handle.get_actual() == target._handle, elem._path
            assert elem is not target, elem._path
            assert target._handle.get_actual() is None, target._path

        for outside in (min(_port_indices(port)) - 1, max(_port_indices(port)) + 1):
            try:
                handle[outside]
            except IndexError:
                continue
            raise AssertionError(f"{port}[{outside}] is outside the port range")


# Verilator does not expose IO declarations for these ports.
PORT_RANGE_AVAILABLE = not SIM_NAME.startswith("verilator")


@xfail_without_if_refs
@cocotb.test()
async def test_sv_if_ref_port_range_is_declared(dut):
    """Test that an array port reports the range it declares"""
    for port, targets in ARRAY_PORT_TARGETS.items():
        handle = getattr(dut.sub_i, port)

        if not PORT_RANGE_AVAILABLE:
            try:
                rng = handle.range
            except RuntimeError:
                continue
            raise AssertionError(f"{port} reported a range of {rng}")

        left, right = ARRAY_PORT_RANGES.get(port, (0, len(targets) - 1))
        assert handle.range == Range(
            left, "to" if left <= right else "downto", right
        ), port
        assert handle.left == left, port
        assert handle.right == right, port


@xfail_without_if_refs
@cocotb.skipif(
    SIM_NAME.startswith("verilator"),
    reason="Verilator exposes interface-array ports only as individual references",
)
@cocotb.test()
async def test_sv_if_ref_array_actual(dut):
    """The actual array has its own bounds and index mapping."""
    reference = dut.sub_i.sv_if_ref_far_up_to_size
    actual = reference._handle.get_actual()
    assert actual is not None
    assert actual.get_name_string() == "sv_if_arr_size"
    assert actual.get_fullname_string() == "top.sv_if_arr_size"
    target = _make_sim_object(actual, actual.get_fullname_string())
    assert target is dut.sv_if_arr_size
    assert reference.range == Range(100, "to", 102)
    assert target.range == Range(0, "to", 2)
    assert reference[100]._handle.get_actual() == target[0]._handle
    assert actual.get_actual() is None


@xfail_without_if_refs
@cocotb.test()
async def test_sv_if_ref_scalar_port_resolves(dut):
    """Test that a scalar port retains its identity while resolving its target"""
    for port, (target_name, target_index) in SCALAR_PORT_TARGETS.items():
        target = _target(dut, target_name, target_index)
        handle = getattr(dut.sub_i, port)
        assert isinstance(handle, HierarchyObject), port
        assert handle._name == port
        assert handle._path == f"top.sub_i.{port}"
        actual = handle._handle.get_actual()
        assert actual is not None, port
        assert actual.get_name_string() == target._name, port
        assert actual.get_fullname_string() == target._path, port
        assert _make_sim_object(actual, actual.get_fullname_string()) is target, port
        assert actual == handle._handle.get_actual(), port
        assert handle is not target, port
        assert target._handle.get_actual() is None, port
        assert handle._def_name == target._def_name, port


@xfail_without_if_refs
@cocotb.test()
async def test_sv_if_ref_port_drives_correct_interface(dut):
    """Test that writing through a port reaches the interface it refers to"""
    concrete_targets = [("sv_if_i", None)]
    concrete_targets += [("sv_if_arr_size", i) for i in range(3)]
    concrete_targets += [("sv_if_arr_up", i) for i in range(3)]
    concrete_targets += [("sv_if_arr_dn", i) for i in range(3)]
    concrete_targets += [("unrelated_name_arr_size", i) for i in range(2)]

    drives = [
        (f"{port}[{port_index}]", getattr(dut.sub_i, port)[port_index], target)
        for port, targets in ARRAY_PORT_TARGETS.items()
        for port_index, target in zip(_port_indices(port), targets)
    ]
    drives += [
        (port, getattr(dut.sub_i, port), target)
        for port, target in SCALAR_PORT_TARGETS.items()
    ]

    # Drive ports separately: they alias, so simultaneous writes can mask errors.
    for value, (label, handle, target) in enumerate(drives, start=1):
        for target_name, target_index in concrete_targets:
            _target(dut, target_name, target_index).value.value = 0
        await Timer(1, "step")

        handle.value.value = value
        await Timer(1, "step")

        moved = [
            _target_path(target_name, target_index)
            for target_name, target_index in concrete_targets
            if _target(dut, target_name, target_index).value.value != 0
        ]
        assert moved == [_target_path(*target)], (
            f"writing {label} moved {moved}, expected {[_target_path(*target)]}"
        )
        assert _target(dut, *target).value.value == value, label


@xfail_without_if_refs
@cocotb.test()
async def test_sv_if_ref_arr_access(dut):
    """Test that elements of an interface reference array can be accessed"""
    for i in range(3):
        assert {"a", "b", "c"} <= set(dut.sub_i.sv_if_ref_size_to_size[i]._keys())


@xfail_without_if_refs
@cocotb.test()
async def test_sv_if_ref_arr_signal_path(dut):
    """Test the reference paths and actual signals in an interface array"""
    for i in range(3):
        signal = dut.sub_i.sv_if_ref_size_to_size[i].b
        assert signal._name == "b"
        assert signal._path == f"top.sub_i.sv_if_ref_size_to_size[{i}].b"
        assert signal._handle.get_actual() == dut.sv_if_arr_size[i].b._handle


@xfail_without_if_refs
@cocotb.test()
async def test_sv_if_ref_arr_read_write(dut):
    """Test reading and writing signals through an interface reference array"""
    for i in range(3):
        dut.sub_i.sv_if_ref_size_to_size[i].b.value = 1
    await Timer(1, "step")
    for i in range(3):
        assert dut.sv_if_arr_size[i].b.value == 1

    for i in range(3):
        dut.sv_if_arr_size[i].b.value = 0
    await Timer(1, "step")
    for i in range(3):
        assert dut.sub_i.sv_if_ref_size_to_size[i].b.value == 0


@xfail_without_if_refs
@cocotb.test()
async def test_sv_if_ref_callbacks(dut):
    """A rebound port element and its target observe the same signal edge."""
    reference = dut.sub_i.sv_if_ref_far_up_to_size[100].a
    actual = reference._handle.get_actual()
    assert actual is not None
    target = _make_sim_object(actual, actual.get_fullname_string())
    assert target is dut.sv_if_arr_size[0].a
    target.value = 0
    await Timer(1, "step")

    target.value = 1
    await with_timeout(Combine(RisingEdge(reference), RisingEdge(target)), 10, "step")
    assert reference.value == 1


@xfail_without_if_refs
@cocotb.test()
async def test_sv_if_ref_nested_array(dut):
    """Array lookup below a reference operates on the target's array."""
    for reference, target in (
        (dut.sub_i.sv_if_ref_scalar_to_scalar, dut.sv_if_i),
        (dut.sub_i.sv_if_ref_dn_to_size[0], dut.sv_if_arr_size[2]),
    ):
        assert reference.data._handle.get_actual() == target.data._handle
        assert reference.data[1]._handle.get_actual() == target.data[1]._handle
        signal = reference.data[1][2]
        assert signal._path == f"{reference._path}.data[1][2]"
        actual = signal._handle.get_actual()
        assert actual is not None
        actual_signal = _make_sim_object(actual, actual.get_fullname_string())
        assert actual_signal is target.data[1][2]
        actual_signal.value = 42
        await Timer(1, "step")
        assert signal.value == 42
        signal.value = 84
        await Timer(1, "step")
        assert actual_signal.value == 84
