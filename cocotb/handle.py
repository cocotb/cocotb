#!/usr/bin/env python

''' Copyright (c) 2013 Potential Ventures Ltd
Copyright (c) 2013 SolarFlare Communications Inc
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd,
      SolarFlare Communications Inc nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. '''

# -*- coding: utf-8 -*-

import logging
import ctypes
import traceback
import sys
import warnings
from io import StringIO, BytesIO

import os

# For autodocumentation don't need the extension modules
if "SPHINX_BUILD" in os.environ:
    simulator = None
else:
    import simulator

import cocotb
from cocotb.binary import BinaryValue
from cocotb.log import SimLog
from cocotb.result import TestError
from cocotb.triggers import _RisingEdge, _FallingEdge
from cocotb.utils import get_python_integer_types




class SimHandleBase(object):
    """
    Base class for all simulation objects.

    We maintain a handle which we can use for GPI calls
    """

    # For backwards compatibility we support a mapping of old member names
    # which may alias with the simulator hierarchy.  In these cases the
    # simulator takes priority, only falling back 
    _compat_mapping = {
        "log"               :       "_log",
        "fullname"          :       "_fullname",
        "name"              :       "_name",
        "setimmediatevalue" :       "_setimmediatevalue"
        }

    def __init__(self, handle):
        """
        Args:
            handle (integer)    : the GPI handle to the simulator object
        """
        self._handle = handle
        self._len = None
        self._sub_handles = {}  # Dictionary of children
        self._discovered = False

        self._name = simulator.get_name_string(self._handle)
        self._fullname = self._name + "(%s)" % simulator.get_type_string(self._handle)
        self._log = SimLog("cocotb.%s" % self._name)
        self._log.debug("Created")

    def __hash__(self):
        return self._handle

    def __getattr__(self, name):
        """
        Query the simulator for a object with the specified name
        and cache the result to build a tree of objects
        """

        if name == "value":
            return self._getvalue()
        if name in self._sub_handles:
            return self._sub_handles[name]
        new_handle = simulator.get_handle_by_name(self._handle, name)
        if not new_handle:
            if name in self._compat_mapping:
                warnings.warn("Use of %s attribute is deprecated" % name)
                return getattr(self, self._compat_mapping[name])
            raise AttributeError("%s contains no object named %s" % (self._name, name))
        self._sub_handles[name] = SimHandle(new_handle)
        return self._sub_handles[name]

    def __hasattr__(self, name):
        """
        Since calling hasattr(handle, "something") will print out a
        backtrace to the log since usually attempting to access a
        non-existent member is an error we provide a 'peek function

        We still add the found handle to our dictionary to prevent leaking
        handles.
        """
        if name in self._sub_handles:
            return self._sub_handles[name]
        new_handle = simulator.get_handle_by_name(self._handle, name)
        if new_handle:
            self._sub_handles[name] = SimHandle(new_handle)
        return new_handle


    def __getitem__(self, index):
        if index in self._sub_handles:
            return self._sub_handles[index]
        new_handle = simulator.get_handle_by_index(self._handle, index)
        if not new_handle:
            self._raise_testerror("%s contains no object at index %d" % (self._name, index))
        self._sub_handles[index] = SimHandle(new_handle)
        return self._sub_handles[index]


    def __cmp__(self, other):

        # Permits comparison of handles i.e. if clk == dut.clk
        if isinstance(other, SimHandleBase):
            if self._handle == other._handle: return 0
            return 1


    def __repr__(self):
        return self._fullname

    def _raise_testerror(self, msg):
        lastframe = sys._getframe(2)
        if sys.version_info[0] >= 3:
            buff = StringIO()
            traceback.print_stack(lastframe, file=buff)
        else:
            buff_bytes = BytesIO()
            traceback.print_stack(lastframe, file=buff_bytes)
            buff = StringIO(buff_bytes.getvalue().decode("UTF8"))
        self._log.error("%s\n%s" % (msg, buff.getvalue()))
        exception = TestError(msg)
        exception.stderr.write(buff.getvalue())
        buff.close()
        raise exception


class HierarchyObject(SimHandleBase):
    """
    Hierarchy objects don't have values, they are effectively scopes or namespaces
    """

    def __setattr__(self, name, value):
        """
        Provide transparent access to signals via the hierarchy

        Slightly hacky version of operator overloading in Python

        Raise an AttributeError if users attempt to create new members which
        don't exist in the design.
        """
        if name.startswith("_") or name in self._compat_mapping:
            return object.__setattr__(self, name, value)
        if self.__hasattr__(name):
            return getattr(self, name)._setcachedvalue(value)
        raise AttributeError("Attempt to access %s which isn't present in %s" %(
            name, self._name))

    def __iter__(self):
        """
        Iterate over all known objects in this layer of hierarchy
        """
        if not self._discovered:
            self._discover_all()

        for name, handle in self._sub_handles.items():
            if isinstance(handle, list):
                for subhdl in handle:
                    yield subhdl

            else:
                yield handle

    def _discover_all(self):
        """
        When iterating or performing tab completion, we run through ahead of
        time and discover all possible children, populating the _sub_handle
        mapping. Hierarchy can't change after elaboration so we only have to
        do this once.
        """
        if self._discovered: return

        iterator = simulator.iterate(self._handle)
        while True:
            try:
                thing = simulator.next(iterator)
            except StopIteration:
                # Iterator is cleaned up internally in GPI
                break
            name = simulator.get_name_string(thing)
            hdl = SimHandle(thing)

            # This is slightly hacky, but we want generate loops to result in a list
            # These are renamed in VHPI to __X where X is the index
            import re
            result = re.match("(?P<name>.*)__(?P<index>\d+)$", name)
            if not result:
                result = re.match("(?P<name>.*)\((?P<index>\d+)", name)

            if result:
                index = int(result.group("index"))
                name = result.group("name")

                if name not in self._sub_handles:
                    self._sub_handles[name] = []
                if len(self._sub_handles[name]) < index + 1:
                    delta = index - len(self._sub_handles[name]) + 1
                    self._sub_handles[name].extend([None]*delta)
                self._sub_handles[name][index] = hdl
            else:
                self._sub_handles[hdl._name.split(".")[-1]] = hdl

        self._discovered = True

    def _getAttributeNames(self):
        """Permits IPython tab completion to work"""
        self._discover_all()
        return dir(self)

class ConstantObject(SimHandleBase):
    """
    Constant objects have a value that can be read, but not set.

    We can also cache the value since it is elaboration time fixed and won't
    change within a simulation
    """
    def __init__(self, handle, *args, **kwargs):
        SimHandleBase.__init__(self, handle)
        self._value = None


    def __int__(self):
        return int(self._value)

    def __repr__(self):
        return repr(int(self))


class NonConstantObject(SimHandleBase):
    def __init__(self, handle):
        """
            Args:
                _handle [integer] : vpi/vhpi handle to the simulator object
        """
        SimHandleBase.__init__(self, handle)
        self._r_edge = _RisingEdge(self)
        self._f_edge = _FallingEdge(self)

    def __hash__(self):
        return self._handle

    def __str__(self):
        return "%s @0x%x" % (self._name, self._handle)

    def __getitem__(self, index):
        if index in self._sub_handles:
            return self._sub_handles[index]
        new_handle = simulator.get_handle_by_index(self._handle, index)
        if not new_handle:
            self._raise_testerror("%s contains no object at index %d" % (self._name, index))
        self._sub_handles[index] = SimHandle(new_handle)
        return self._sub_handles[index]

    def _getvalue(self):
        result = BinaryValue()
        result.binstr = self._get_value_str()
        return result

    ## We want to maintain compatability with python 2.5 so we can't use @property with a setter
    #value = property(_getvalue, None, None, "A reference to the value")

    def _get_value_str(self):
        return simulator.get_signal_val(self._handle)

    def __len__(self):
        """Returns the 'length' of the underlying object.

        For vectors this is the number of bits.

        TODO: Handle other types (loops, generate etc)
        """
        if self._len is None:
            self._len = len(self._get_value_str())
        return self._len


    def __cmp__(self, other):

        # Permits comparison of handles i.e. if clk == dut.clk
        if isinstance(other, SimHandle):
            if self._handle == other._handle: return 0
            return 1

        # Use the comparison method of the other object against our value
        return self.value.__cmp__(other)


    def __int__(self):
        return int(self.value)

    def __repr__(self):
        return repr(int(self))

class ModifiableObject(NonConstantObject):
    """
    Base class for simulator objects whose values can be modified
    """

    def __setitem__(self, index, value):
        """Provide transparent assignment to bit index"""
        self.__getitem__(index)._setcachedvalue(value)

    def _setimmediatevalue(self, value):
        """
        Set the value of the underlying simulation object to value.

        Args:
            value (ctypes.Structure, cocotb.binary.BinaryValue, int, double)
                The value to drive onto the simulator object

        Raises:
            TypeError

        This operation will fail unless the handle refers to a modifiable
        object eg net, signal or variable.

        We determine the library call to make based on the type of the value

        Assigning integers less than 32-bits is faster
        """
        if isinstance(value, get_python_integer_types()) and value < 0x7fffffff:
            simulator.set_signal_val(self._handle, value)
            return

        if isinstance(value, ctypes.Structure):
            value = BinaryValue(value=cocotb.utils.pack(value), bits=len(self))
        elif isinstance(value, get_python_integer_types()):
            value = BinaryValue(value=value, bits=len(self), bigEndian=False)
        elif not isinstance(value, BinaryValue):
            self._log.critical("Unsupported type for value assignment: %s (%s)" % (type(value), repr(value)))
            raise TypeError("Unable to set simulator value with type %s" % (type(value)))

        simulator.set_signal_val_str(self._handle, value.binstr)

    def _getvalue(self):
        result = BinaryValue()
        result.binstr = self._get_value_str()
        return result

    def _setcachedvalue(self, value):
        """
        Intercept the store of a value and hold in cache.

        This operation is to enable all of the scheduled callbacks to completed
        with the same read data and for the writes to occour on the next
        sim time
        """
        cocotb.scheduler.save_write(self, value)


    # We want to maintain compatability with python 2.5 so we can't use @property with a setter
    value = property(_getvalue, _setcachedvalue, None, "A reference to the value")


    def __le__(self, value):
        """Overload the less than or equal to operator to
            provide an hdl-like shortcut
                module.signal <= 2
        """
        self.value = value



class RealObject(ModifiableObject):
    """
    Specific object handle for Real signals and variables
    """

    def _setimmediatevalue(self, value):
        """
        Set the value of the underlying simulation object to value.

        Args:
            value (float)
                The value to drive onto the simulator object

        Raises:
            TypeError

        This operation will fail unless the handle refers to a modifiable
        object eg net, signal or variable.
        """
        if not isinstance(value, float):
            self._log.critical("Unsupported type for real value assignment: %s (%s)" % (type(value), repr(value)))
            raise TypeError("Unable to set simulator value with type %s" % (type(value)))

        simulator.set_signal_val_real(self._handle, value)

    def _getvalue(self):
        return simulator.get_signal_val_real(self._handle)

    # We want to maintain compatability with python 2.5 so we can't use @property with a setter
    value = property(_getvalue, ModifiableObject._setcachedvalue, None, "A reference to the value")

    def __float__(self):
        return self._getvalue()


def SimHandle(handle):
    """
    Factory function to create the correct type of SimHandle object
    """

    _type2cls = {
        simulator.MODULE:      HierarchyObject,
        simulator.REG:         ModifiableObject,
        simulator.REAL:        RealObject
    }

    t = simulator.get_type(handle)
    if t not in _type2cls:
        raise TestError("Couldn't find a matching object for GPI type %d" % t)
    return _type2cls[t](handle)

