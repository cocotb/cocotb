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
#from StringIO import StringIO

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

class SimHandle(object):

    def __init__(self, handle):
        """
            Args:
                _handle [integer] : vpi/vhpi handle to the simulator object
        """
        self._handle = handle           # handle used for future simulator transactions
        self._sub_handles = {}          # Dictionary of SimHandle objects created by getattr
        self._len = None

        self.name = simulator.get_name_string(self._handle)
        self.fullname = self.name + '(%s)' % simulator.get_type_string(self._handle)
        self.log = SimLog('cocotb.' + self.name)
        self.log.debug("Created!")
        self._r_edge = _RisingEdge(self)
        self._f_edge = _FallingEdge(self)

    def __hash__(self):
        return self._handle

    def __str__(self):
        return "%s @0x%x" % (self.name, self._handle)

    def __getattr__(self, name):
        """ Query the simulator for a object with the specified name
            and cache the result to build a tree
        """
        if name in self._sub_handles:
            return self._sub_handles[name]
        new_handle = simulator.get_handle_by_name(self._handle, name)
        if not new_handle:
            self._raise_testerror("%s contains no object named %s" % (self.name, name))
        self._sub_handles[name] = SimHandle(new_handle)
        return self._sub_handles[name]

    def _raise_testerror(self, msg):
        lastframe = sys._getframe(2)
        if sys.version_info[0] >= 3:
            buff = StringIO()
            traceback.print_stack(lastframe, file=buff)
        else:
            buff_bytes = BytesIO()
            traceback.print_stack(lastframe, file=buff_bytes)
            buff = StringIO(buff_bytes.getvalue().decode("UTF8"))
        self.log.error("%s\n%s" % (msg, buff.getvalue()))
        exception = TestError(msg)
        exception.stderr.write(buff.getvalue())
        buff.close()
        raise exception

    def __setattr__(self, name, value):
        """Provide transparent access to signals"""
        if not name.startswith('_') and not name in ["name", "fullname", "log", "value"] \
                                                     and self.__hasattr__(name):
            getattr(self, name).setcachedvalue(value)
            return
        object.__setattr__(self, name, value)

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
            self._raise_testerror("%s contains no object at index %d" % (self.name, index))
        self._sub_handles[index] = SimHandle(new_handle)
        return self._sub_handles[index]

    def __setitem__(self, index, value):
        """Provide transparent assignment to bit index"""
        self.__getitem__(index).setcachedvalue(value)

    def getvalue(self):
        result = BinaryValue()
        result.binstr = self._get_value_str()
        return result

    def setimmediatevalue(self, value):
        """
        Set the value of the underlying simulation object to value.

        Args:
            value (ctypes.Structure, cocotb.binary.BinaryValue, int)
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
            self.log.critical("Unsupported type for value assignment: %s (%s)" % (type(value), repr(value)))
            raise TypeError("Unable to set simulator value with type %s" % (type(value)))

        simulator.set_signal_val_str(self._handle, value.binstr)

    def setcachedvalue(self, value):
        """Intercept the store of a value and hold in cache.

        This operation is to enable all of the scheduled callbacks to completed
        with the same read data and for the writes to occour on the next
        sim time"""
        cocotb.scheduler.save_write(self, value)

    # We want to maintain compatability with python 2.5 so we can't use @property with a setter
    value = property(getvalue, setcachedvalue, None, "A reference to the value")

    def _get_value_str(self):
        return simulator.get_signal_val(self._handle)

    def __le__(self, value):
        """Overload the less than or equal to operator to
            provide an hdl-like shortcut
                module.signal <= 2
        """
        self.value = value


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


    def __iter__(self):
        """Iterates over all known types defined by simulator module"""
        for handle_type in [simulator.MODULE,
                            simulator.PARAMETER,
                            simulator.REG,
                            simulator.NET,
                            simulator.NETARRAY]:
            iterator = simulator.iterate(handle_type, self._handle)
            while True:
                try:
                    thing = simulator.next(iterator)
                except StopIteration:
                    break
                hdl = SimHandle(thing)
                self._sub_handles[hdl.name] = hdl
                yield hdl

    def __int__(self):
        return int(self.value)


