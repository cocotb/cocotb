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

import enum
import logging
import re
from abc import ABC, abstractmethod
from functools import lru_cache
from logging import Logger
from typing import (
    Any,
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
)

import cocotb
from cocotb import simulator
from cocotb._deprecation import deprecated
from cocotb._py_compat import cached_property
from cocotb.types import Logic, LogicArray
from cocotb.types.range import Range


class _Limits(enum.IntEnum):
    SIGNED_NBIT = 1
    UNSIGNED_NBIT = 2
    VECTOR_NBIT = 3


@lru_cache(maxsize=None)
def _value_limits(n_bits, limits):
    """Calculate min/max for given number of bits and limits class"""
    if limits == _Limits.SIGNED_NBIT:
        min_val = -(2 ** (n_bits - 1))
        max_val = 2 ** (n_bits - 1) - 1
    elif limits == _Limits.UNSIGNED_NBIT:
        min_val = 0
        max_val = 2**n_bits - 1
    else:
        min_val = -(2 ** (n_bits - 1))
        max_val = 2**n_bits - 1

    return min_val, max_val


class SimHandleBase(ABC):
    """Base class for all simulation objects.

    All simulation objects are hashable and equatable by identity.

    .. code-block:: python3
        a = dut.clk
        b = dut.clk
        assert a == b

    .. versionchanged:: 2.0
        ``get_definition_name()`` and ``get_definition_file()`` were removed in favor of :meth:`_def_name` and :meth:`_def_file`, respectively.
    """

    @abstractmethod
    def __init__(self, handle: simulator.gpi_sim_hdl, path: Optional[str]) -> None:
        self._handle = handle
        self._path: str = self._name if path is None else path
        """The path to this handle, or its name if this is the root handle.

        :meta public:
        """

    @cached_property
    def _name(self) -> str:
        """The name of an object.

        :meta public:
        """
        return self._handle.get_name_string()

    @cached_property
    def _type(self) -> str:
        """The type of an object as a string.

        :meta public:
        """
        return self._handle.get_type_string()

    @cached_property
    def _log(self) -> Logger:
        """The logging object.

        :meta public:
        """
        return logging.getLogger(f"cocotb.{self._name}")

    @cached_property
    def _def_name(self) -> str:
        """The name of a GPI object's definition.

        This is the value of ``vpiDefName`` for VPI, ``vhpiNameP`` for VHPI,
        and ``mti_GetPrimaryName`` for FLI.
        Support for this depends on the specific object type and simulator used.

        :meta public:
        """
        return self._handle.get_definition_name()

    @cached_property
    def _def_file(self) -> str:
        """The name of the file that sources the object's definition.

        This is the value of ``vpiDefFile`` for VPI, ``vhpiFileNameP`` for VHPI,
        and ``mti_GetRegionSourceName`` for FLI.
        Support for this depends on the specific object type and simulator used.

        :meta public:
        """
        return self._handle.get_definition_file()

    def __hash__(self) -> int:
        return hash(self._handle)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, SimHandleBase):
            return NotImplemented
        return self._handle == other._handle

    def __repr__(self) -> str:
        desc = self._path
        defname = self._def_name
        if defname:
            desc += " with definition " + defname
            deffile = self._def_file
            if deffile:
                desc += " (at " + deffile + ")"
        return type(self).__qualname__ + "(" + desc + ")"


#: Type of keys (name or index) in HierarchyObjectBase.
KeyType = TypeVar("KeyType")


class HierarchyObjectBase(SimHandleBase, Generic[KeyType]):
    """Base class for hierarchical objects.

    Hierarchical objects don't have values, they are just scopes/namespaces of other objects.
    This includes array-like hierarchical structures like "generate loops"
    and named hierarchical structures like "generate blocks" or "module"/"entity" instantiations.

    This base class defines logic to discover, cache, and inspect child objects.
    It provides a :class:`dict`-like interface for doing so.

    :meth:`_keys`, :meth:`_values`, and :meth:`_items` mimic their :class:`dict` counterparts.
    You can also iterate over an object, which returns child objects, not keys like in :class:`dict`;
    and can check the :func:`len`.

    See :class:`HierarchyObject` and :class:`HierarchyArrayObject` for examples.
    """

    @abstractmethod
    def __init__(self, handle: simulator.gpi_sim_hdl, path: Optional[str]) -> None:
        super().__init__(handle, path)
        self._sub_handles: Dict[KeyType, SimHandleBase] = {}

    def _keys(self) -> Iterable[KeyType]:
        """Iterate over the keys (name or index) of the child objects.

        :meta public:
        """
        self._discover_all()
        return self._sub_handles.keys()

    def _values(self) -> Iterable[SimHandleBase]:
        """Iterate over the child objects.

        :meta public:
        """
        self._discover_all()
        return self._sub_handles.values()

    def _items(self) -> Iterable[Tuple[KeyType, SimHandleBase]]:
        """Iterate over ``(key, object)`` tuples of child objects.

        :meta public:
        """
        self._discover_all()
        return self._sub_handles.items()

    @lru_cache(maxsize=None)
    def _discover_all(self) -> None:
        """When iterating or performing IPython tab completion, we run through ahead of
        time and discover all possible children, populating the :any:`_sub_handles`
        mapping. Hierarchy can't change after elaboration so we only have to
        do this once.
        """
        for thing in self._handle.iterate(simulator.OBJECTS):
            name = thing.get_name_string()

            # translate HDL name into a consistent key name
            try:
                key = self._sub_handle_key(name)
            except ValueError:
                self._log.exception(
                    "Unable to translate handle >%s< to a valid _sub_handle key",
                    name,
                )
                continue

            # compute a full path using the key name
            path = self._child_path(key)

            # attempt to create the child object
            try:
                hdl = SimHandle(thing, path)
            except NotImplementedError:
                self._log.exception(
                    "Unable to construct a SimHandle object for %s", path
                )
                continue

            # add to cache
            self._sub_handles[key] = hdl

    def __getitem__(self, key: KeyType) -> SimHandleBase:
        # try to use cached value
        try:
            return self._sub_handles[key]
        except KeyError:
            pass

        # try to get value from GPI
        new_handle = self._get_handle_by_key(key)
        if not new_handle:
            raise KeyError(f"{self._path} contains no child object named {key}")

        # if successful, construct and cache
        sub_handle = SimHandle(new_handle, self._child_path(key))
        self._sub_handles[key] = sub_handle

        return sub_handle

    @abstractmethod
    def _get_handle_by_key(self, key: KeyType) -> Optional[simulator.gpi_sim_hdl]:
        """Get child object by key from the simulator.

        Args:
            key: The key of the child object.

        Returns:
            A raw simulator handle for the child object at the given key, or ``None``.
        """

    @abstractmethod
    def _child_path(self, key: KeyType) -> str:
        """Compute the path string of a child object at the given key.

        Args:
            key: The key of the child object.

        Returns:
            A path string of the child object at the a given key.
        """

    @abstractmethod
    def _sub_handle_key(self, name: str) -> KeyType:
        """Translate a discovered child object name into a key.

        Args:
            name: The GPI name of the child object.

        Returns:
            A unique key for the child object.

        Raises:
            ValueError: if unable to translate handle to a valid _sub_handle key.
        """

    def __iter__(self) -> Iterable[SimHandleBase]:
        return iter(self._values())

    def __len__(self) -> int:
        self._discover_all()
        return len(self._sub_handles)

    def __dir__(self) -> List[str]:
        """Permits IPython tab completion and debuggers to work."""
        self._discover_all()
        return super().__dir__() + [str(k) for k in self._keys()]


class HierarchyObject(HierarchyObjectBase[str]):
    r"""Named hierarchical scope objects.

    This class is used for named hierarchical structures, such as "generate blocks" or "module"/"entity" instantiations.

    Children under this structure are found by using the name of the child with either the attribute syntax or index syntax.
    For example, if in your :envvar:`TOPLEVEL` entity/module you have a signal/net named ``count``, you could do either of the following.

    .. code-block:: python3

        dut.count  # attribute syntax
        dut["count"]  # index syntax

    Attribute syntax is usually shorter and easier to read, and is more common.
    However, it has limitations:

    - the name cannot start with a number
    - the name cannot start with a ``_`` character
    - the name can only contain ASCII letters, numbers, and the ``_`` character

    Any possible name of an object is supported with the index syntax,
    but it can be more verbose.

    .. note::
        If you need to access signals/nets that start with ``_``,
        or use escaped identifier (Verilog) or extended identifier (VHDL) characters,
        you have to use the index syntax.
        Accessing escaped/extended identifiers requires enclosing the name
        with leading and trailing double backslashes (``\\``).

        .. code-block:: python3

            dut["_underscore_signal]
            dut["\\%extended !ID\\"]

    Iteration yields all child objects in no particular order.
    The :func:`len` function can be used to find the number of children.

    .. code-block:: python3

        # discover all children in 'some_module'
        total = 0
        for handle in dut.some_module:
            cocotb.log("Found %r", handle._path)
            total += 1

        # make sure we found them all
        assert len(dut.some_module) == total
    """

    def __init__(self, handle: simulator.gpi_sim_hdl, path: Optional[str]) -> None:
        super().__init__(handle, path)

    def __setattr__(self, name: str, value: Any) -> None:
        # private attributes pass through directly
        if name.startswith("_"):
            return object.__setattr__(self, name, value)

        raise AttributeError(f"{self._name} contains no object named {name}")

    def __getattr__(self, name: str) -> SimHandleBase:
        if name.startswith("_"):
            return object.__getattribute__(self, name)

        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(str(e)) from None

    @deprecated(
        "Use `handle[child_name]` syntax instead. If extended identifiers are needed simply add a '\\' character before and after the name."
    )
    def _id(self, name: str, extended: bool = True) -> SimHandleBase:
        """Query the simulator for an object with the specified *name*.

        If *extended* is ``True``, run the query only for VHDL extended identifiers.
        For Verilog, only ``extended=False`` is supported.

        .. deprecated:: 2.0
            Use ``handle[child_name]`` syntax instead.
            If extended identifiers are needed simply add a ``\\`` character before and after the name.

        :meta public:
        """
        if extended:
            name = "\\" + name + "\\"

        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(str(e)) from None

    def _child_path(self, name: str) -> str:
        delimiter = "::" if self._type == "GPI_PACKAGE" else "."
        return f"{self._path}{delimiter}{name}"

    def _sub_handle_key(self, name: str) -> str:
        return name.rsplit(".", 1)[-1]

    def _get_handle_by_key(self, key: str) -> Optional[simulator.gpi_sim_hdl]:
        return self._handle.get_handle_by_name(key)


class HierarchyArrayObject(HierarchyObjectBase[int]):
    """Arrays of hierarchy objects.

    This class is used for array-like hierarchical structures like "generate loops".

    Children of this object are found by supplying a numerical index using index syntax.
    For example, if you have a design with a generate loop ``gen_pipe_stages`` from the range ``0`` to ``7``:

    .. code-block:: python3

        block_0 = dut.gen_pipe_stages[0]
        block_7 = dut.gen_pipe_stages[7]

    Iteration yields all child objects in order.

    .. code-block:: python3

        # set all 'reg's in each pipe stage to 0
        for pipe_stage in dut.gen_pipe_stages:
            pipe_stage.reg.value = 0

    Use the :meth:`range` property if you want to iterate over the indexes.
    The :func:`len` function can be used to find the number of elements.

    .. code-block:: python3

        # set all 'reg's in each pipe stage to 0
        for idx in dut.gen_pipe_stages.range:
            dut.gen_pipe_stages[idx].reg.value = 0

        # make sure we have all the pipe stages
        assert len(dut.gen_pipe_stage) == len(dut.gen_pipe_stages.range)
    """

    def __init__(self, handle: simulator.gpi_sim_hdl, path: Optional[str]) -> None:
        super().__init__(handle, path)

    def _sub_handle_key(self, name: str) -> int:
        # This is slightly hacky, but we need to extract the index from the name
        # See also GEN_IDX_SEP_* in VhpiImpl.h for the VHPI separators.
        #
        # FLI and VHPI:       _name(X) where X is the index
        # VHPI(ALDEC):        _name__X where X is the index
        # VPI:                _name[X] where X is the index
        result = re.match(rf"{self._name}__(?P<index>\d+)$", name)
        if not result:
            result = re.match(rf"{self._name}\((?P<index>\d+)\)$", name, re.IGNORECASE)
        if not result:
            result = re.match(rf"{self._name}\[(?P<index>\d+)\]$", name)

        if result:
            return int(result.group("index"))
        else:
            raise ValueError(f"Unable to match an index pattern: {name}")

    def _child_path(self, key: int) -> str:
        return f"{self._path}[{key}]"

    def _get_handle_by_key(self, key: int) -> Optional[simulator.gpi_sim_hdl]:
        return self._handle.get_handle_by_index(key)

    def __getitem__(self, key: int) -> SimHandleBase:
        if isinstance(key, slice):
            raise TypeError("Slice indexing is not supported")
        try:
            return super().__getitem__(key)
        except KeyError as e:
            raise IndexError(str(e)) from None

    @cached_property
    def range(self) -> Range:
        """Return a :class:`~cocotb.types.Range` over the indexes of the array/vector."""
        left, right = self._handle.get_range()

        # guess direction based on length until we can get that from the GPI
        length = self._handle.get_num_elems()
        if length == 0:
            direction = "to" if left < right else "downto"
        else:
            direction = "to" if left <= right else "downto"

        return Range(left, direction, right)

    def left(self) -> int:
        """Return the leftmost index in the array/vector."""
        return self.range.left

    def direction(self) -> str:
        """Return the direction (``"to"``/``"downto"``) of indexes in the array/vector."""
        return self.range.direction

    def right(self) -> int:
        """Return the rightmost index in the array/vector."""
        return self.range.right

    # ideally `__len__` could be implemented in terms of `range`

    def __iter__(self) -> Iterable[SimHandleBase]:
        # must use `sorted(self._keys())` instead of the range because `range` doesn't work universally.
        for i in sorted(self._keys()):
            yield self[i]


class NonHierarchyObject(SimHandleBase):
    """Common base class for all non-hierarchy objects."""

    @property
    def value(self):
        """The value of this simulation object.

        .. note::
            When setting this property, the value is stored by the :class:`~cocotb.scheduler.Scheduler`
            and all stored values are written at the same time at the end of the current simulator time step.

            Use :meth:`setimmediatevalue` to set the value immediately.
        """
        raise TypeError(
            f"Not permissible to get values of object {self._name} of type {type(self)}"
        )

    @value.setter
    def value(self, value):
        if self.is_const:
            raise TypeError(f"{self._path} is constant")
        self._set_value(value, cocotb.scheduler._schedule_write)

    def setimmediatevalue(self, value):
        """Assign a value to this simulation object immediately."""
        if self.is_const:
            raise TypeError(f"{self._path} is constant")

        def _call_now(handle, f, *args):
            f(*args)

        self._set_value(value, _call_now)

    @cached_property
    def is_const(self) -> bool:
        """``True`` if the simulator object is immutable, e.g. a Verilog parameter or VHDL constant or generic."""
        return self._handle.get_const()

    def _set_value(self, value, call_sim):
        """This should be overriden in subclasses.

        This is used to implement both the setter for :attr:`value`, and the
        :meth:`setimmediatevalue` method.

        ``call_sim(handle, f, *args)`` should be used to schedule simulator writes,
        rather than performing them directly as ``f(*args)``.
        """
        raise TypeError(
            f"Not permissible to set values on object {self._name} of type {type(self)}"
        )


class NonHierarchyIndexableObjectBase(NonHierarchyObject):
    @abstractmethod
    def __init__(self, handle, path):
        super().__init__(handle, path)
        self._sub_handles: Dict[int, SimHandleBase] = {}

    @cached_property
    def _range(self) -> Tuple[int, int]:
        return self._handle.get_range()

    def __getitem__(self, index):
        if isinstance(index, slice):
            raise IndexError("Slice indexing is not supported")
        if self._range is None:
            raise IndexError(f"{self._path} is not indexable.")
        if index in self._sub_handles:
            return self._sub_handles[index]
        new_handle = self._handle.get_handle_by_index(index)
        if not new_handle:
            raise IndexError(f"{self._path} contains no object at index {index}")
        path = self._path + "[" + str(index) + "]"
        self._sub_handles[index] = SimHandle(new_handle, path)
        return self._sub_handles[index]

    def __iter__(self):
        if self._range is None:
            return

        for i in self._range_iter(self._range[0], self._range[1]):
            try:
                result = self[i]
                yield result
            except IndexError:
                continue

    def _range_iter(self, left, right):
        if left > right:
            while left >= right:
                yield left
                left = left - 1
        else:
            while left <= right:
                yield left
                left = left + 1

    @lru_cache(maxsize=None)
    def __len__(self) -> int:
        return self._handle.get_num_elems()


class NonHierarchyIndexableObject(NonHierarchyIndexableObjectBase):
    """A non-hierarchy indexable object.

    Getting and setting the current value of an array is done
    by iterating through sub-handles in left-to-right order.

    Given an HDL array ``arr``:

    +--------------+---------------------+--------------------------------------------------------------+
    | Verilog      | VHDL                | ``arr.value`` is equivalent to                               |
    +==============+=====================+==============================================================+
    | ``arr[4:7]`` | ``arr(4 to 7)``     | ``[arr[4].value, arr[5].value, arr[6].value, arr[7].value]`` |
    +--------------+---------------------+--------------------------------------------------------------+
    | ``arr[7:4]`` | ``arr(7 downto 4)`` | ``[arr[7].value, arr[6].value, arr[5].value, arr[4].value]`` |
    +--------------+---------------------+--------------------------------------------------------------+

    When setting the signal as in ``arr.value = ...``, the same index equivalence as noted in the table holds.

    .. warning::
        Assigning a value to a sub-handle:

        - **Wrong**: ``dut.some_array.value[0] = 1`` (gets value as a list then updates index 0)
        - **Correct**: ``dut.some_array[0].value = 1``
    """

    def __init__(self, handle, path):
        super().__init__(handle, path)

    @NonHierarchyObject.value.getter
    def value(self) -> list:
        # Don't use self.__iter__, because it has an unwanted `except IndexError`
        return [self[i].value for i in self._range_iter(self._range[0], self._range[1])]

    def _set_value(self, value, call_sim):
        """Assign value from a list of same length to an array in left-to-right order.
        Index 0 of the list maps to the left-most index in the array.

        See the docstring for this class.
        """
        if type(value) is not list:  # noqa: E721
            raise TypeError(
                f"Assigning non-list value to object {self._name} of type {type(self)}"
            )
        if len(value) != len(self):
            raise ValueError(
                "Assigning list of length %d to object %s of length %d"
                % (len(value), self._name, len(self))
            )
        for val_idx, self_idx in enumerate(
            self._range_iter(self._range[0], self._range[1])
        ):
            self[self_idx]._set_value(value[val_idx], call_sim)


class _SetAction:
    """Base class representing the type of action used while write-accessing a handle."""

    pass


class _SetValueAction(_SetAction):
    __slots__ = ("value",)
    """Base class representing the type of action used while write-accessing a handle with a value."""

    def __init__(self, value):
        self.value = value


class Deposit(_SetValueAction):
    """Action used for placing a value into a given handle."""

    def _as_gpi_args_for(self, hdl):
        return self.value, 0  # GPI_DEPOSIT


class Force(_SetValueAction):
    """Action used to force a handle to a given value until a release is applied."""

    def _as_gpi_args_for(self, hdl):
        return self.value, 1  # GPI_FORCE


class Freeze(_SetAction):
    """Action used to make a handle keep its current value until a release is used."""

    def _as_gpi_args_for(self, hdl):
        return hdl.value, 1  # GPI_FORCE


class Release(_SetAction):
    """Action used to stop the effects of a previously applied force/freeze action."""

    def _as_gpi_args_for(self, hdl):
        return 0, 2  # GPI_RELEASE


class ModifiableObject(NonHierarchyObject):
    """Base class for simulator objects whose values can be modified."""

    def drivers(self):
        """An iterator for gathering all drivers for a signal.

        This is currently only available for VPI.
        Also, only a few simulators implement this.
        """
        return self._handle.iterate(simulator.DRIVERS)

    def loads(self):
        """An iterator for gathering all loads on a signal.

        This is currently only available for VPI.
        Also, only a few simulators implement this.
        """
        return self._handle.iterate(simulator.LOADS)

    def _check_for_set_action(self, value):
        if not isinstance(value, _SetAction):
            return value, 0  # GPI_DEPOSIT
        return value._as_gpi_args_for(self)


class LogicObject(ModifiableObject, NonHierarchyIndexableObjectBase):
    """Specific object handle for Verilog nets and regs and VHDL std_logic and std_logic_vectors"""

    def __init__(self, handle, path):
        super().__init__(handle, path)

    def _set_value(self, value, call_sim):
        """Set the value of the underlying simulation object to *value*.

        This operation will fail unless the handle refers to a modifiable
        object, e.g. net, signal or variable.

        We determine the library call to make based on the type of the value
        because assigning integers less than 32 bits is faster.

        Args:
            value (cocotb.types.LogicArray, int):
                The value to drive onto the simulator object.

        Raises:
            TypeError: If target has an unsupported type for value assignment.

            OverflowError: If int value is out of the range that can be represented
                by the target. -2**(Nbits - 1) <= value <= 2**Nbits - 1

        .. versionchanged:: 2.0
            Using :class:`ctypes.Structure` objects to set values was removed.
            Convert the struct object to a :class:`~cocotb.types.LogicArray` before assignment using
            ``LogicArray("".join(format(int(byte), "08b") for byte in bytes(struct_obj)))`` instead.

        .. versionchanged:: 2.0
            Using :class:`dict` objects to set values was removed.
            Convert the dictionary to an integer before assignment using
            ``sum(v << (d['bits'] * i) for i, v in enumerate(d['values']))``.
        """
        value, set_action = self._check_for_set_action(value)

        if isinstance(value, int):
            min_val, max_val = _value_limits(len(self), _Limits.VECTOR_NBIT)
            if min_val <= value <= max_val:
                if len(self) <= 32:
                    call_sim(self, self._handle.set_signal_val_int, set_action, value)
                    return

                if value < 0:
                    value = LogicArray(
                        value,
                        Range(len(self) - 1, "downto", 0),
                    )
                else:
                    value = LogicArray(
                        value,
                        Range(len(self) - 1, "downto", 0),
                    )
            else:
                raise OverflowError(
                    "Int value ({!r}) out of range for assignment of {!r}-bit signal ({!r})".format(
                        value, len(self), self._name
                    )
                )

        elif isinstance(value, LogicArray):
            if len(self) != len(value):
                raise ValueError(
                    f"cannot assign value of length {len(value)} to handle of length {len(self)}"
                )

        elif isinstance(value, Logic):
            if len(self) != 1:
                raise ValueError(
                    f"cannot assign value of length 1 to handle of length {len(self)}"
                )
            value = LogicArray([value])

        else:
            raise TypeError(
                f"Unsupported type for value assignment: {type(value)} ({value!r})"
            )

        call_sim(self, self._handle.set_signal_val_binstr, set_action, value.binstr)

    @ModifiableObject.value.getter
    def value(self) -> LogicArray:
        binstr = self._handle.get_signal_val_binstr()
        return LogicArray(binstr)


class RealObject(ModifiableObject):
    """Specific object handle for Real signals and variables."""

    def __init__(self, handle, path):
        super().__init__(handle, path)

    def _set_value(self, value, call_sim):
        """Set the value of the underlying simulation object to value.

        This operation will fail unless the handle refers to a modifiable
        object, e.g. net, signal or variable.

        Args:
            value (float): The value to drive onto the simulator object.

        Raises:
            TypeError: If target has an unsupported type for
                real value assignment.
        """
        value, set_action = self._check_for_set_action(value)

        try:
            value = float(value)
        except ValueError:
            raise TypeError(
                f"Unsupported type for real value assignment: {type(value)} ({value!r})"
            )

        call_sim(self, self._handle.set_signal_val_real, set_action, value)

    @ModifiableObject.value.getter
    def value(self) -> float:
        return self._handle.get_signal_val_real()


class EnumObject(ModifiableObject):
    """Specific object handle for enumeration signals and variables."""

    def __init__(self, handle, path):
        super().__init__(handle, path)

    def _set_value(self, value, call_sim):
        """Set the value of the underlying simulation object to *value*.

        This operation will fail unless the handle refers to a modifiable
        object, e.g. net, signal or variable.

        Args:
            value (int): The value to drive onto the simulator object.

        Raises:
            TypeError: If target has an unsupported type for
                 integer value assignment.
        """
        value, set_action = self._check_for_set_action(value)

        if not isinstance(value, int):
            raise TypeError(
                f"Unsupported type for enum value assignment: {type(value)} ({value!r})"
            )

        min_val, max_val = _value_limits(32, _Limits.UNSIGNED_NBIT)
        if min_val <= value <= max_val:
            call_sim(self, self._handle.set_signal_val_int, set_action, value)
        else:
            raise OverflowError(
                "Int value ({!r}) out of range for assignment of enum signal ({!r})".format(
                    value, self._name
                )
            )

    @ModifiableObject.value.getter
    def value(self) -> int:
        return self._handle.get_signal_val_long()


class IntegerObject(ModifiableObject):
    """Specific object handle for integer and enumeration signals and variables."""

    def __init__(self, handle, path):
        super().__init__(handle, path)

    def _set_value(self, value, call_sim):
        """Set the value of the underlying simulation object to *value*.

        This operation will fail unless the handle refers to a modifiable
        object, e.g. net, signal or variable.

        Args:
            value (int): The value to drive onto the simulator object.

        Raises:
            TypeError: If target has an unsupported type for
                 integer value assignment.

            OverflowError: If value is out of range for assignment
                 of 32-bit IntegerObject.
        """
        value, set_action = self._check_for_set_action(value)

        if not isinstance(value, int):
            raise TypeError(
                "Unsupported type for integer value assignment: {} ({!r})".format(
                    type(value), value
                )
            )

        min_val, max_val = _value_limits(32, _Limits.SIGNED_NBIT)
        if min_val <= value <= max_val:
            call_sim(self, self._handle.set_signal_val_int, set_action, value)
        else:
            raise OverflowError(
                "Int value ({!r}) out of range for assignment of integer signal ({!r})".format(
                    value, self._name
                )
            )

    @ModifiableObject.value.getter
    def value(self) -> int:
        return self._handle.get_signal_val_long()


class StringObject(ModifiableObject, NonHierarchyIndexableObjectBase):
    """Specific object handle for String variables."""

    def __init__(self, handle, path):
        super().__init__(handle, path)

    def _set_value(self, value, call_sim):
        """Set the value of the underlying simulation object to *value*.

        This operation will fail unless the handle refers to a modifiable
        object, e.g. net, signal or variable.

        Args:
            value (bytes): The value to drive onto the simulator object.

        Raises:
            TypeError: If target has an unsupported type for
                 string value assignment.

        .. versionchanged:: 1.4
            Takes :class:`bytes` instead of :class:`str`.
            Users are now expected to choose an encoding when using these objects.

        """
        value, set_action = self._check_for_set_action(value)

        if not isinstance(value, bytes):
            raise TypeError(
                "Unsupported type for string value assignment: {} ({!r})".format(
                    type(value), value
                )
            )

        call_sim(self, self._handle.set_signal_val_str, set_action, value)

    @ModifiableObject.value.getter
    def value(self) -> bytes:
        return self._handle.get_signal_val_str()


_handle2obj = {}

_type2cls = {
    simulator.MODULE: HierarchyObject,
    simulator.STRUCTURE: HierarchyObject,
    simulator.REG: LogicObject,
    simulator.NET: LogicObject,
    simulator.NETARRAY: NonHierarchyIndexableObject,
    simulator.REAL: RealObject,
    simulator.INTEGER: IntegerObject,
    simulator.ENUM: EnumObject,
    simulator.STRING: StringObject,
    simulator.GENARRAY: HierarchyArrayObject,
    simulator.PACKAGE: HierarchyObject,
}


def SimHandle(handle, path=None):
    """Factory function to create the correct type of `SimHandle` object.

    Args:
        handle (int): The GPI handle to the simulator object.
        path (str): Path to this handle, ``None`` if root.

    Returns:
        The `SimHandle` object.

    Raises:
        NotImplementedError: If no matching object for GPI type could be found.
    """

    # Enforce singletons since it's possible to retrieve handles avoiding
    # the hierarchy by getting driver/load information
    try:
        return _handle2obj[handle]
    except KeyError:
        pass

    t = handle.get_type()
    if t not in _type2cls:
        raise NotImplementedError(
            "Couldn't find a matching object for GPI type %s(%d) (path=%s)"
            % (handle.get_type_string(), t, path)
        )
    obj = _type2cls[t](handle, path)
    _handle2obj[handle] = obj
    return obj
