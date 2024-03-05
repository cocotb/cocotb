# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import cocotb
from cocotb.handle import HierarchyArrayObject, HierarchyObjectBase

SIM_NAME = cocotb.SIM_NAME.lower()


# GHDL is unable to access signals in generate loops (gh-2594)
# Verilator doesn't support vpiGenScope or vpiGenScopeArray (gh-1884)


def iter_module(mod: cocotb.handle.ModifiableObject, depth=0):
    yield mod, depth

    if isinstance(mod, (HierarchyObjectBase, HierarchyArrayObject)):
        for obj in mod:
            yield from iter_module(obj, depth + 1)


def get_len(obj):
    return len(obj) if hasattr(obj, "__len__") else None


@cocotb.test()
async def test_structure(dut):
    """
    Tests that name, fullname, handle type, and length match accross simulators.
    Not all of the match at the moment, but we can use this to measure progress.
    """

    # TODO store and check the outputs

    for obj, depth in iter_module(dut):
        objlen = get_len(obj)
        objtype = type(obj).__qualname__
        treeinfo = f"{'  ' * depth}{obj._name}: {objtype}[{objlen}]"
        print(f"{treeinfo:50} {obj._path}")


@cocotb.test()
async def test_name_matches_iter(dut):
    """
    Test name accessibility and handle lengths.
    
     All of the names accessible through iteration are also accessible through the name.
     Multiple instances in Python don't corrupt C++ handle lengths, particularly pseudo objects.
    """

    t = cocotb.handle.HierarchyObject(dut._handle, dut._path)
    assert id(t) != id(dut)

    objs = [obj for obj, _depth in iter_module(dut)]

    # this gives "RuntimeError: dictionary changed size during iteration" on verilator / intf_arr
    # for obj, _depth in iter_module(dut):

    for obj in objs:
        print(obj._path)
        objlen = get_len(obj)

        direct_obj = eval(obj._path)
        assert obj._handle == direct_obj._handle

        if get_len(obj) != objlen:
            raise Exception("eval of copy changed underlying length")
