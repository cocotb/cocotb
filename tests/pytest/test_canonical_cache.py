# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys
import types
from typing import Any

# Ensure mock cocotb.simulator is registered before importing cocotb
if "cocotb.simulator" not in sys.modules:
    m = types.ModuleType("cocotb.simulator")
    m.OBJECTS = 0
    m.MODULE = 1
    m.STRUCTURE = 2
    m.PACKED = 3
    m.LOGIC = 4
    m.LOGIC_ARRAY = 5
    m.NETARRAY = 6
    m.REAL = 7
    m.INTEGER = 8
    m.ENUM = 9
    m.STRING = 10
    m.FIXED_STRING = 11
    m.GENARRAY = 12
    m.PACKAGE = 13
    m.RANGE_NO_DIR = 0
    m.RANGE_UP = 1
    m.RANGE_DOWN = 2
    m.RISING = 1
    m.FALLING = 2
    m.VALUE_CHANGE = 3
    m.sim_obj = types.SimpleNamespace  # type: ignore[attr-defined]
    m.sim_callback = types.SimpleNamespace  # type: ignore[attr-defined]
    sys.modules["cocotb.simulator"] = m

if "cocotb" not in sys.modules:
    c = types.ModuleType("cocotb")
    c.__file__ = "src/cocotb/__init__.py"
    c.__path__ = ["src/cocotb"]
    c.simulator = sys.modules["cocotb.simulator"]  # type: ignore[attr-defined]
    sys.modules["cocotb"] = c

import cocotb.handle
from cocotb.handle import HierarchyObject


class _FakeSimObj:
    def __init__(self, **kwargs: Any) -> None:
        self.__dict__.update(kwargs)


def _make_mock_dut() -> tuple[HierarchyObject, _FakeSimObj]:
    clk_sim_obj = _FakeSimObj(
        get_type=lambda: sys.modules["cocotb.simulator"].LOGIC,
        get_type_string=lambda: "GPI_LOGIC",
        get_name_string=lambda: "clk",
        get_type_name=lambda: "logic",
        get_definition_name=lambda: "logic",
        get_definition_file=lambda: "test.v",
        get_num_elems=lambda: 1,
        get_indexable=lambda: 0,
        get_concrete_path=lambda: None,
    )

    dut_sim_obj = _FakeSimObj(
        get_type=lambda: sys.modules["cocotb.simulator"].MODULE,
        get_type_string=lambda: "GPI_MODULE",
        get_name_string=lambda: "dut",
        get_type_name=lambda: "module",
        get_definition_name=lambda: "module",
        get_definition_file=lambda: "dut.v",
        get_handle_by_name=lambda name, discovery_method=0: (
            clk_sim_obj if name.lower() == "clk" else None
        ),
        iterate=lambda kind: iter([clk_sim_obj]),
        get_concrete_path=lambda: None,
    )

    dut = HierarchyObject(dut_sim_obj, "dut")
    return dut, clk_sim_obj


def test_lookup_caching_uses_canonical_name() -> None:
    """Test that lookup with non-canonical casing caches object by canonical name."""
    dut, _ = _make_mock_dut()

    # Look up using non-canonical casing 'CLK'
    obj_upper = dut._get("CLK")
    assert obj_upper is not None
    assert obj_upper._path == "dut.clk"

    # Cached exclusively under canonical name
    assert "clk" in dut._sub_handles
    assert "CLK" not in dut._sub_handles

    # Subsequent lookup with canonical casing returns the exact same object
    obj_lower = dut._get("clk")
    assert obj_lower is obj_upper

    # Subsequent lookup with non-canonical casing also returns the exact same cached object
    obj_upper_again = dut._get("CLK")
    assert obj_upper_again is obj_upper

    # Sub-handles dictionary only has the single canonical entry
    assert list(dut._sub_handles.keys()) == ["clk"]


def test_discovery_after_lookup_does_not_duplicate() -> None:
    """Test that discovery after a non-canonical lookup doesn't duplicate the handle."""
    dut, _ = _make_mock_dut()

    obj_upper = dut._get("CLK")
    assert obj_upper is not None

    # Discover all should not duplicate or overwrite
    dut._discover_all()
    assert list(dut._sub_handles.keys()) == ["clk"]
    assert dut._sub_handles["clk"] is obj_upper


def test_lookup_after_discovery_returns_cached_object() -> None:
    """Test that lookup with non-canonical name returns object already discovered."""
    dut, _ = _make_mock_dut()

    dut._discover_all()
    assert "clk" in dut._sub_handles
    assert len(dut._sub_handles) == 1

    # Lookup with non-canonical name returns the discovered object
    obj_upper = dut._get("CLK")
    assert obj_upper is dut._sub_handles["clk"]
    assert len(dut._sub_handles) == 1
    assert "CLK" not in dut._sub_handles
