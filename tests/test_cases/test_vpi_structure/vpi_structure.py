# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd,
#       SolarFlare Communications Inc nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

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
