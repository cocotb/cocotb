#!/usr/bin/env python

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

# -*- coding: utf-8 -*-

import ctypes
import warnings

import os

if "COCOTB_SIM" in os.environ:
    import simulator
else:
    simulator = None

import cocotb
from cocotb.binary import BinaryValue
from cocotb.log import SimLog
from cocotb.result import TestError
from cocotb import _py_compat

# Only issue a warning for each deprecated attribute access
_deprecation_warned = {}


class SimHandleBase(object):
    """Base class for all simulation objects.

    We maintain a handle which we can use for GPI calls.
    """

    # For backwards compatibility we support a mapping of old member names
    # which may alias with the simulator hierarchy.  In these cases the
    # simulator result takes priority, only falling back to the python member
    # if there is no colliding object in the elaborated design.
    _compat_mapping = {
        "log"               :       "_log",
        "fullname"          :       "_fullname",
        "name"              :       "_name",
        }

    def __init__(self, handle, path):
        """
        Args:
            handle (integer)    : the GPI handle to the simulator object
            path (string)       : path to this handle, None if root
        """
        self._handle = handle
        self._len = None
        self._sub_handles = {}  # Dictionary of children
        self._invalid_sub_handles = {}  # Dictionary of invalid queries

        self._name = simulator.get_name_string(self._handle)
        self._type = simulator.get_type_string(self._handle)
        self._fullname = self._name + "(%s)" % self._type
        self._path = self._name if path is None else path
        self._log = SimLog("cocotb.%s" % self._name)
        self._log.debug("Created")
        self._def_name = simulator.get_definition_name(self._handle)
        self._def_file = simulator.get_definition_file(self._handle)

    def get_definition_name(self):
        return object.__getattribute__(self, "_def_name")

    def get_definition_file(self):
        return object.__getattribute__(self, "_def_file")

    def __hash__(self):
        return self._handle

    def __len__(self):
        """Returns the 'length' of the underlying object.

        For vectors this is the number of bits.
        """
        if self._len is None:
            self._len = simulator.get_num_elems(self._handle)
        return self._len

    def __eq__(self, other):

        # Permits comparison of handles i.e. if clk == dut.clk
        if isinstance(other, SimHandleBase):
            if self._handle == other._handle:
                return 0
            return 1

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        desc = self._path
        defname = object.__getattribute__(self, "_def_name")
        if defname:
            desc += " with definition "+defname
            deffile = object.__getattribute__(self, "_def_file")
            if deffile:
                desc += " (at "+deffile+")"
        return type(self).__name__ + "(" + desc + ")"

    def __str__(self):
        return self._path

    def __setattr__(self, name, value):
        if name in self._compat_mapping:
            if name not in _deprecation_warned:
                warnings.warn("Use of %s attribute is deprecated" % name)
                _deprecation_warned[name] = True
            return setattr(self, self._compat_mapping[name], value)
        else:
            return object.__setattr__(self, name, value)

    def __getattr__(self, name):
        if name in self._compat_mapping:
            if name not in _deprecation_warned:
                warnings.warn("Use of %s attribute is deprecated" % name)
                _deprecation_warned[name] = True
            return getattr(self, self._compat_mapping[name])
        else:
            return object.__getattr__(self, name)

class RegionObject(SimHandleBase):
    """Region objects don't have values, they are effectively scopes or namespaces."""
    def __init__(self, handle, path):
        SimHandleBase.__init__(self, handle, path)
        self._discovered = False

    def __iter__(self):
        """Iterate over all known objects in this layer of hierarchy."""
        try:
            if not self._discovered:
                self._discover_all()

            for name, handle in self._sub_handles.items():
                if isinstance(handle, list):
                    self._log.debug("Found index list length %d", len(handle))
                    for subindex, subhdl in enumerate(handle):
                        if subhdl is None:
                            self._log.warning("Index %d doesn't exist in %s.%s", subindex, self._name, name)
                            continue
                        self._log.debug("Yielding index %d from %s (%s)", subindex, name, type(subhdl))
                        yield subhdl
                else:
                    self._log.debug("Yielding %s (%s)", name, handle)
                    yield handle
        except GeneratorExit:
            pass

    def _discover_all(self):
        """When iterating or performing tab completion, we run through ahead of
        time and discover all possible children, populating the ``_sub_handles``
        mapping. Hierarchy can't change after elaboration so we only have to
        do this once.
        """
        if self._discovered:
            return
        self._log.debug("Discovering all on %s", self._name)
        iterator = simulator.iterate(self._handle, simulator.OBJECTS)
        while True:
            try:
                thing = simulator.next(iterator)
            except StopIteration:
                # Iterator is cleaned up internally in GPI
                break
            name = simulator.get_name_string(thing)
            try:
                hdl = SimHandle(thing, self._child_path(name))
            except TestError as e:
                self._log.debug("%s", e)
                continue

            key = self._sub_handle_key(name)

            if key is not None:
                self._sub_handles[key] = hdl
            else:
                self._log.debug("Unable to translate handle >%s< to a valid _sub_handle key", hdl._name)
                continue

        self._discovered = True

    def _child_path(self, name):
        """Returns a string of the path of the child :any:`SimHandle` for a given name."""
        return self._path + "." + name

    def _sub_handle_key(self, name):
        """Translates the handle name to a key to use in ``_sub_handles`` dictionary."""
        return name.split(".")[-1]

    def __dir__(self):
        """Permits IPython tab completion to work."""
        self._discover_all()
        return super(RegionObject, self).__dir__() + [str(k) for k in self._sub_handles]


class HierarchyObject(RegionObject):
    """Hierarchy objects are namespace/scope objects."""

    def __setattr__(self, name, value):
        """Provide transparent access to signals via the hierarchy.

        Slightly hacky version of operator overloading in Python.

        Raise an :exc:`AttributeError` if users attempt to create new members which
        don't exist in the design.
        """
        if name.startswith("_"):
            return SimHandleBase.__setattr__(self, name, value)
        if self.__hasattr__(name) is not None:
            sub = self.__getattr__(name)
            if type(sub) is NonHierarchyIndexableObject:
                if type(value) is not list:
                    raise AttributeError("Attempting to set %s which is a NonHierarchyIndexableObject to something other than a list?" % (name))

                if len(sub) != len(value):
                    raise IndexError("Attempting to set %s with list length %d but target has length %d" % (
                        name, len(value), len(sub)))
                for idx in range(len(value)):
                    sub[idx] = value[idx]
                return
            else:
                return sub._setcachedvalue(value)
        if name in self._compat_mapping:
            return SimHandleBase.__setattr__(self, name, value)
        raise AttributeError("Attempt to access %s which isn't present in %s" %(
            name, self._name))

    def __getattr__(self, name):
        """Query the simulator for a object with the specified name
        and cache the result to build a tree of objects.
        """
        try:
            return self._sub_handles[name]
        except KeyError:
            pass

        if name.startswith("_"):
            return SimHandleBase.__getattr__(self, name)

        new_handle = simulator.get_handle_by_name(self._handle, name)

        if not new_handle:
            if name in self._compat_mapping:
                return SimHandleBase.__getattr__(self, name)
            raise AttributeError("%s contains no object named %s" % (self._name, name))

        sub_handle = SimHandle(new_handle, self._child_path(name))
        self._sub_handles[name] = sub_handle
        return sub_handle

    def __hasattr__(self, name):
        """Since calling ``hasattr(handle, "something")`` will print out a
        backtrace to the log (since usually attempting to access a
        non-existent member is an error) we provide a 'peek' function.

        We still add the found handle to our dictionary to prevent leaking
        handles.
        """
        if name in self._sub_handles:
            return self._sub_handles[name]

        if name in self._invalid_sub_handles:
            return None

        new_handle = simulator.get_handle_by_name(self._handle, name)
        if new_handle:
            self._sub_handles[name] = SimHandle(new_handle, self._child_path(name))
        else:
            self._invalid_sub_handles[name] = None
        return new_handle

    def _id(self, name, extended=True):
        """Query the simulator for a object with the specified name,
        including extended identifiers,
        and cache the result to build a tree of objects.
        """
        if extended:
            name = "\\"+name+"\\"

        if self.__hasattr__(name) is not None:
            return getattr(self, name)
        raise AttributeError("%s contains no object named %s" % (self._name, name))

class HierarchyArrayObject(RegionObject):
    """Hierarchy Arrays are containers of Hierarchy Objects."""

    def _sub_handle_key(self, name):
        """Translates the handle name to a key to use in ``_sub_handles`` dictionary."""
        # This is slightly hacky, but we need to extract the index from the name
        #
        # FLI and VHPI(IUS):  _name(X) where X is the index
        # VHPI(ALDEC):        _name__X where X is the index
        # VPI:                _name[X] where X is the index
        import re
        result = re.match(r"{0}__(?P<index>\d+)$".format(self._name), name)
        if not result:
            result = re.match(r"{0}\((?P<index>\d+)\)$".format(self._name), name)
        if not result:
            result = re.match(r"{0}\[(?P<index>\d+)\]$".format(self._name), name)

        if result:
            return int(result.group("index"))
        else:
            self._log.error("Unable to match an index pattern: %s", name)
            return None

    def __len__(self):
        """Returns the 'length' of the generate block."""
        if self._len is None:
            if not self._discovered:
                self._discover_all()

            self._len = len(self._sub_handles)
        return self._len

    def __getitem__(self, index):
        if isinstance(index, slice):
            raise IndexError("Slice indexing is not supported")
        if index in self._sub_handles:
            return self._sub_handles[index]
        new_handle = simulator.get_handle_by_index(self._handle, index)
        if not new_handle:
            raise IndexError("%s contains no object at index %d" % (self._name, index))
        path = self._path + "[" + str(index) + "]"
        self._sub_handles[index] = SimHandle(new_handle, path)
        return self._sub_handles[index]

    def _child_path(self, name):
        """Returns a string of the path of the child :any:`SimHandle` for a given name."""
        index = self._sub_handle_key(name)
        return self._path + "[" + str(index) + "]"

    def __setitem__(self, index, value):
        raise TypeError("Not permissible to set %s at index %d" % (self._name, index))


class AssignmentResult(object):
    """
    Object that exists solely to provide an error message if the caller
    is not aware of cocotb's meaning of ``<=``.
    """
    def __init__(self, signal, value):
        self._signal = signal
        self._value = value

    def __bool__(self):
        raise TypeError(
            "Attempted to use `{0._signal!r} <= {0._value!r}` (a cocotb "
            "delayed write) as if it were a numeric comparison. To perform "
            "comparison, use `{0._signal!r}.value <= {0._value!r}` instead."
            .format(self)
        )

    # python 2
    __nonzero__ = __bool__


class NonHierarchyObject(SimHandleBase):
    """Common base class for all non-hierarchy objects."""

    def __init__(self, handle, path):
        SimHandleBase.__init__(self, handle, path)

    def __iter__(self):
        return iter(())

    def _getvalue(self):
        if type(self) is NonHierarchyIndexableObject:
            # need to iterate over the sub-object
            result = []
            for x in range(len(self)):
                result.append(self[x]._getvalue())
            return result
        else:
            raise TypeError("Not permissible to get values on object %s type %s" % (self._name, type(self)))

    def setimmediatevalue(self, value):
        raise TypeError("Not permissible to set values on object %s type %s" % (self._name, type(self)))

    def _setcachedvalue(self, value):
        raise TypeError("Not permissible to set values on object %s type %s" % (self._name, type(self)))

    def __le__(self, value):
        """Overload the less than or equal to operator to
            provide an hdl-like shortcut
                module.signal <= 2
        """
        self.value = value
        return AssignmentResult(self, value)

    def __eq__(self, other):
        if isinstance(other, SimHandleBase):
            if self._handle == other._handle:
                return 0
            return 1

        # Use the comparison method of the other object against our value
        return self.value == other

    def __ne__(self, other):
        return not self.__eq__(other)


    # We want to maintain compatibility with python 2.5 so we can't use @property with a setter
    value = property(fget=lambda self: self._getvalue(),
                     fset=lambda self, v: self._setcachedvalue(v),
                     fdel=None,
                     doc="A reference to the value")

    # Re-define hash because Python 3 has issues when using the above property
    def __hash__(self):
        return SimHandleBase.__hash__(self)

class ConstantObject(NonHierarchyObject):
    """Constant objects have a value that can be read, but not set.

    We can also cache the value since it is elaboration time fixed and won't
    change within a simulation.
    """
    def __init__(self, handle, path, handle_type):
        NonHierarchyObject.__init__(self, handle, path)
        if handle_type in [simulator.INTEGER, simulator.ENUM]:
            self._value = simulator.get_signal_val_long(self._handle)
        elif handle_type == simulator.REAL:
            self._value = simulator.get_signal_val_real(self._handle)
        elif handle_type == simulator.STRING:
            self._value = simulator.get_signal_val_str(self._handle)
        else:
            val = simulator.get_signal_val_binstr(self._handle)
            self._value = BinaryValue(n_bits=len(val))
            try:
                self._value.binstr = val
            except Exception:
                self._value = val

    def __int__(self):
        return int(self.value)

    def __float__(self):
        return float(self.value)

    def _getvalue(self):
        return self._value

    def __str__(self):
        return str(self.value)

class NonHierarchyIndexableObject(NonHierarchyObject):
    def __init__(self, handle, path):
        """Args:
            handle (int): FLI/VPI/VHPI handle to the simulator object.
        """
        NonHierarchyObject.__init__(self, handle, path)
        self._range = simulator.get_range(self._handle)

    def __setitem__(self, index, value):
        """Provide transparent assignment to indexed array handles."""
        if type(value) is list:
            if len(value) != len(self.__getitem__(index)):
                raise IndexError("Assigning list of length %d to object %s of length %d" % (
                    len(value), self.__getitem__(index)._fullname, len(self.__getitem__(index))))
            self._log.info("Setting item %s to %s", self.__getitem__(index)._fullname, value)
            for idx in range(len(value)):
                self.__getitem__(index).__setitem__(idx, value[idx])
        else:
            self.__getitem__(index).value = value

    def __getitem__(self, index):
        if isinstance(index, slice):
            raise IndexError("Slice indexing is not supported")
        if self._range is None:
            raise IndexError("%s is not indexable.  Unable to get object at index %d" % (self._fullname, index))
        if index in self._sub_handles:
            return self._sub_handles[index]
        new_handle = simulator.get_handle_by_index(self._handle, index)
        if not new_handle:
            raise IndexError("%s contains no object at index %d" % (self._fullname, index))
        path = self._path + "[" + str(index) + "]"
        self._sub_handles[index] = SimHandle(new_handle, path)
        return self._sub_handles[index]

    def __iter__(self):
        try:
            if self._range is None:
                return

            self._log.debug("Iterating with range [%d:%d]", self._range[0], self._range[1])
            for i in self._range_iter(self._range[0], self._range[1]):
                try:
                    result = self[i]
                    yield result
                except IndexError:
                    continue
        except GeneratorExit:
            pass


    def _range_iter(self, left, right):
        try:
            if left > right:
                while left >= right:
                    yield left
                    left = left - 1
            else:
                while left <= right:
                    yield left
                    left = left + 1
        except GeneratorExit:
            pass

class NonConstantObject(NonHierarchyIndexableObject):
    # FIXME: what is the difference to ModifiableObject? Explain in docstring.

    def __init__(self, handle, path):
        """Args:
            handle (int): FLI/VPI/VHPI handle to the simulator object.
        """
        NonHierarchyIndexableObject.__init__(self, handle, path)

    def drivers(self):
        """An iterator for gathering all drivers for a signal."""
        try:
            iterator = simulator.iterate(self._handle, simulator.DRIVERS)
            while True:
                # Path is left as the default None since handles are not derived from the hierarchy
                yield SimHandle(simulator.next(iterator))
        except GeneratorExit:
            pass

    def loads(self):
        """An iterator for gathering all loads on a signal."""
        try:
            iterator = simulator.iterate(self._handle, simulator.LOADS)
            while True:
                # Path is left as the default None since handles are not derived from the hierarchy
                yield SimHandle(simulator.next(iterator))
        except GeneratorExit:
            pass


class ModifiableObject(NonConstantObject):
    """Base class for simulator objects whose values can be modified."""

    def setimmediatevalue(self, value):
        """Set the value of the underlying simulation object to value.

        This operation will fail unless the handle refers to a modifiable
        object, e.g. net, signal or variable.

        We determine the library call to make based on the type of the value
        because assigning integers less than 32 bits is faster.

        Args:
            value (ctypes.Structure, cocotb.binary.BinaryValue, int, double):
                The value to drive onto the simulator object.

        Raises:
            TypeError: If target is not wide enough or has an unsupported type
                 for value assignment.
        """
        if isinstance(value, _py_compat.integer_types) and value < 0x7fffffff and len(self) <= 32:
            simulator.set_signal_val_long(self._handle, value)
            return

        if isinstance(value, ctypes.Structure):
            value = BinaryValue(value=cocotb.utils.pack(value), n_bits=len(self))
        elif isinstance(value, _py_compat.integer_types):
            value = BinaryValue(value=value, n_bits=len(self), bigEndian=False)
        elif isinstance(value, dict):
            # We're given a dictionary with a list of values and a bit size...
            num = 0
            vallist = list(value["values"])
            vallist.reverse()
            if len(vallist) * value["bits"] != len(self):
                self._log.critical("Unable to set with array length %d of %d bit entries = %d total, target is only %d bits long",
                                   len(value["values"]), value["bits"], len(value["values"]) * value["bits"], len(self))
                raise TypeError("Unable to set with array length %d of %d bit entries = %d total, target is only %d bits long" %
                                (len(value["values"]), value["bits"], len(value["values"]) * value["bits"], len(self)))

            for val in vallist:
                num = (num << value["bits"]) + val
            value = BinaryValue(value=num, n_bits=len(self), bigEndian=False)

        elif not isinstance(value, BinaryValue):
            self._log.critical("Unsupported type for value assignment: %s (%s)", type(value), repr(value))
            raise TypeError("Unable to set simulator value with type %s" % (type(value)))

        simulator.set_signal_val_str(self._handle, value.binstr)

    def _getvalue(self):
        binstr = simulator.get_signal_val_binstr(self._handle)
        result = BinaryValue(binstr, len(binstr))
        return result

    def _setcachedvalue(self, value):
        """Intercept the store of a value and hold in cache.

        This operation is to enable all of the scheduled callbacks to complete
        with the same read data and for the writes to occur on the next
        sim time.
        """
        cocotb.scheduler.save_write(self, value)

    def __int__(self):
        return int(self.value)

    def __str__(self):
        return str(self.value)

class RealObject(ModifiableObject):
    """Specific object handle for Real signals and variables."""

    def setimmediatevalue(self, value):
        """Set the value of the underlying simulation object to value.

        This operation will fail unless the handle refers to a modifiable
        object, e.g. net, signal or variable.

        Args:
            value (float): The value to drive onto the simulator object.

        Raises:
            TypeError: If target has an unsupported type for
                real value assignment.
        """
        if not isinstance(value, float):
            self._log.critical("Unsupported type for real value assignment: %s (%s)", type(value), repr(value))
            raise TypeError("Unable to set simulator value with type %s" % (type(value)))

        simulator.set_signal_val_real(self._handle, value)

    def _getvalue(self):
        return simulator.get_signal_val_real(self._handle)

    def __float__(self):
        return float(self.value)

class EnumObject(ModifiableObject):
    """Specific object handle for enumeration signals and variables."""

    def setimmediatevalue(self, value):
        """Set the value of the underlying simulation object to value.

        This operation will fail unless the handle refers to a modifiable
        object, e.g. net, signal or variable.

        Args:
            value (int): The value to drive onto the simulator object.

        Raises:
            TypeError: If target has an unsupported type for
                 integer value assignment.
        """
        if isinstance(value, BinaryValue):
            value = int(value)
        elif not isinstance(value, _py_compat.integer_types):
            self._log.critical("Unsupported type for integer value assignment: %s (%s)", type(value), repr(value))
            raise TypeError("Unable to set simulator value with type %s" % (type(value)))

        simulator.set_signal_val_long(self._handle, value)

    def _getvalue(self):
        return simulator.get_signal_val_long(self._handle)


class IntegerObject(ModifiableObject):
    """Specific object handle for Integer and Enum signals and variables."""

    def setimmediatevalue(self, value):
        """Set the value of the underlying simulation object to value.

        This operation will fail unless the handle refers to a modifiable
        object, e.g. net, signal or variable.

        Args:
            value (int): The value to drive onto the simulator object.

        Raises:
            TypeError: If target has an unsupported type for
                 integer value assignment.
        """
        if isinstance(value, BinaryValue):
            value = int(value)
        elif not isinstance(value, _py_compat.integer_types):
            self._log.critical("Unsupported type for integer value assignment: %s (%s)", type(value), repr(value))
            raise TypeError("Unable to set simulator value with type %s" % (type(value)))

        simulator.set_signal_val_long(self._handle, value)

    def _getvalue(self):
        return simulator.get_signal_val_long(self._handle)

class StringObject(ModifiableObject):
    """Specific object handle for String variables."""

    def setimmediatevalue(self, value):
        """Set the value of the underlying simulation object to value.

        This operation will fail unless the handle refers to a modifiable
        object, e.g. net, signal or variable.

        Args:
            value (str): The value to drive onto the simulator object.

        Raises:
            TypeError: If target has an unsupported type for
                 string value assignment.
        """
        if not isinstance(value, str):
            self._log.critical("Unsupported type for string value assignment: %s (%s)", type(value), repr(value))
            raise TypeError("Unable to set simulator value with type %s" % (type(value)))

        simulator.set_signal_val_str(self._handle, value)

    def _getvalue(self):
        return simulator.get_signal_val_str(self._handle)

_handle2obj = {}

def SimHandle(handle, path=None):
    """Factory function to create the correct type of :any:`SimHandle` object."""
    _type2cls = {
        simulator.MODULE:      HierarchyObject,
        simulator.STRUCTURE:   HierarchyObject,
        simulator.REG:         ModifiableObject,
        simulator.NETARRAY:    NonHierarchyIndexableObject,
        simulator.REAL:        RealObject,
        simulator.INTEGER:     IntegerObject,
        simulator.ENUM:        EnumObject,
        simulator.STRING:      StringObject,
        simulator.GENARRAY:    HierarchyArrayObject,
    }

    # Enforce singletons since it's possible to retrieve handles avoiding
    # the hierarchy by getting driver/load information
    global _handle2obj
    try:
        return _handle2obj[handle]
    except KeyError:
        pass

    t = simulator.get_type(handle)

    # Special case for constants
    if simulator.get_const(handle) and t not in [simulator.MODULE,
                                                 simulator.STRUCTURE,
                                                 simulator.NETARRAY,
                                                 simulator.GENARRAY]:
        obj = ConstantObject(handle, path, t)
        _handle2obj[handle] = obj
        return obj

    if t not in _type2cls:
        raise TestError("Couldn't find a matching object for GPI type %d (path=%s)" % (t, path))
    obj = _type2cls[t](handle, path)
    _handle2obj[handle] = obj
    return obj
