# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
from io import StringIO

import cocotb
from cocotb.handle import HierarchyArrayObject, HierarchyObjectBase

SIM_NAME = cocotb.SIM_NAME.lower()


def iter_module(mod, depth=0):
    yield mod, depth

    if isinstance(mod, (HierarchyObjectBase, HierarchyArrayObject)):
        subs = sorted(
            [obj for obj in mod],
            key=lambda x: str(isinstance(x, HierarchyObjectBase)) + x._name,
        )
        for obj in subs:
            yield from iter_module(obj, depth + 1)


def get_len(obj):
    return len(obj) if hasattr(obj, "__len__") else None


class verify_output:
    def __init__(self, expected_output_file, update=False):
        self.expected_output_file = expected_output_file
        self.captured_output = StringIO()
        self.update = update

    def print(self, st):
        print(st)
        print(st, file=self.captured_output)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.captured_output.seek(0)
        # check if exists
        if self.update:
            with open(self.expected_output_file, "w") as f:
                f.write(self.captured_output.getvalue())
            return

        if not os.path.exists(self.expected_output_file):
            raise FileNotFoundError(
                f"Expected output file {self.expected_output_file} does not exist"
            )

        with open(self.expected_output_file) as f:
            expected_output = f.read()

        if self.captured_output.getvalue() != expected_output:
            raise ValueError(
                f"Output does not match expected:\n{self.captured_output.getvalue()}"
            )


@cocotb.test()
async def test_structure(dut):
    """
    Tests that name, fullname, handle type, and length match across simulators.

    Not all of them match at the moment, but we can use this to measure progress.
    """
    sim_name = cocotb.SIM_NAME.lower().split()[0]

    try:
        with verify_output(
            f"test_structure.{sim_name}.out", update=cocotb.plusargs.get("update")
        ) as f:
            for obj, depth in iter_module(dut):
                objlen = (
                    f"[{get_len(obj)}]"
                    if isinstance(obj, cocotb.handle.ValueObjectBase)
                    else ""
                )
                objtype = type(obj).__qualname__
                treeinfo = f"{'  ' * depth}{obj._name}: {objtype}{objlen}"
                f.print(f"{treeinfo:50} {obj._path}")
    except FileNotFoundError:
        cocotb.log.warning(
            f"No expected output file found for {sim_name}. Pass plusarg +update to update output file"
        )


class DirectLenMismatch(Exception):
    pass


class NameMismatch(Exception):
    pass


class IteratedLenMismatch(Exception):
    pass


@cocotb.test(
    skip=SIM_NAME.startswith("riviera"),
    expect_error=DirectLenMismatch
    if SIM_NAME.startswith(("icarus", "verilator", "xmsim", "modelsim"))
    else (),
)
async def test_direct_matches_iter(dut):
    """
    Test name accessibility and handle lengths.

    All of the names accessible through iteration are also accessible through the name.
    Multiple instances in Python don't corrupt C++ handle lengths, particularly pseudo objects.
    """

    t = cocotb.handle.HierarchyObject(dut._handle, dut._path)

    # We need to ensure that these are different objects, so the iteration tree (dut)
    # doesn't fill in the _sub_handles for the direct access tree (t)
    assert id(t) != id(dut)

    objs = [obj for obj, _depth in iter_module(dut)]

    for obj in objs:
        cocotb.log.info(obj._path)
        objlen = get_len(obj)

        direct_obj = eval(obj._path)
        if obj != direct_obj:
            raise NameMismatch(f"{obj._path} != {direct_obj._path}")

        if get_len(direct_obj) != objlen:
            d_obj = f"direct_obj={direct_obj}[{get_len(direct_obj)}]"
            o_obj = f"obj={obj}[{objlen}]"
            raise DirectLenMismatch(
                f"len of direct object does not match iterated object {d_obj}, {o_obj}"
            )

        if get_len(obj) != objlen:
            raise IteratedLenMismatch("eval of copy changed underlying length")
