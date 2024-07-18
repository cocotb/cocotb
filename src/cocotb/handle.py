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

import collections.abc
import enum
import logging
import re
from abc import ABC, abstractmethod
from functools import lru_cache
from logging import Logger
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    Iterator,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

import cocotb._conf
from cocotb import simulator
from cocotb._deprecation import deprecated
from cocotb._py_compat import cached_property
from cocotb.types import Array, Logic, LogicArray, Range


def _write_now(
    _: "ValueObjectBase[Any, Any]", f: Callable[..., None], args: Any
) -> None:
    f(*args)


if cocotb._conf.trust_inertial:
    _inertial_write = _write_now
else:

    def _inertial_write(
        handle: "ValueObjectBase[Any, Any]", f: Callable[..., None], args: Any
    ) -> None:
        import cocotb._write_scheduler

        cocotb._write_scheduler.schedule_write(handle, f, args)


class _Limits(enum.IntEnum):
    SIGNED_NBIT = 1
    UNSIGNED_NBIT = 2
    VECTOR_NBIT = 3


@lru_cache(maxsize=None)
def _value_limits(n_bits: int, limits: _Limits) -> Tuple[int, int]:
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


class RangeableObjectMixin(SimHandleBase):
    """Base class for simulation objects that have a range."""

    @cached_property
    def range(self) -> Range:
        """Return a :class:`~cocotb.types.Range` over the indexes of the array/vector."""
        left, right = self._handle.get_range()

        # In VHDL ranges like "0 downto 10" represent "null ranges".
        # Left is 0, right is 10, but the number of elements is 0.
        # This logic is to detect null ranges and set the direction appropriately,
        # at least until we can get this information directly from the GPI.
        length = self._handle.get_num_elems()
        if length == 0:
            direction = "downto" if left <= right else "to"
        else:
            direction = "to" if left <= right else "downto"

        return Range(left, direction, right)

    @property
    def left(self) -> int:
        """Return the leftmost index in the array/vector."""
        return self.range.left

    @property
    def direction(self) -> str:
        """Return the direction (``"to"``/``"downto"``) of indexes in the array/vector."""
        return self.range.direction

    @property
    def right(self) -> int:
        """Return the rightmost index in the array/vector."""
        return self.range.right

    def __len__(self) -> int:
        return len(self.range)


#: Type of keys (name or index) in HierarchyObjectBase.
KeyType = TypeVar("KeyType")


class HierarchyObjectBase(SimHandleBase, Generic[KeyType]):
    """Base class for hierarchical simulation objects.

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

    def __iter__(self) -> Iterator[SimHandleBase]:
        return iter(self._values())

    def __len__(self) -> int:
        self._discover_all()
        return len(self._sub_handles)

    def __dir__(self) -> Iterable[str]:
        """Permits IPython tab completion and debuggers to work."""
        self._discover_all()
        return set(super().__dir__()) | {str(k) for k in self._keys()}


class HierarchyObject(HierarchyObjectBase[str]):
    r"""A simulation object that is a name-indexed collection of hierarchical simulation objects.

    This class is used for named hierarchical structures, such as "generate blocks" or "module"/"entity" instantiations.

    Children under this structure are found by using the name of the child with either the attribute syntax or index syntax.
    For example, if in your :envvar:`COCOTB_TOPLEVEL` entity/module you have a signal/net named ``count``, you could do either of the following.

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

    Accessing a non-existent child with attribute syntax results in an :class:`AttributeError`,
    and accessing a non-existent child with index syntax results in a :class:`KeyError`.

    .. note::
        If you need to access signals/nets that start with ``_``,
        or use escaped identifier (Verilog) or extended identifier (VHDL) characters,
        you have to use the index syntax.
        Accessing escaped/extended identifiers requires enclosing the name
        with leading and trailing double backslashes (``\\``).

        .. code-block:: python3

            dut["_underscore_signal"]
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
            return object.__getattribute__(self, name)  # type: ignore

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

        :meta public:

        Args:
            name: The child object by name.
            extended: If ``True``, treat the *name* as an extended identifier.

        Returns:
            The child object.

        Raises:
            AttributeError: If the child object is not found.

        .. deprecated:: 2.0
            Use ``handle[child_name]`` syntax instead.
            If extended identifiers are needed simply add a ``\\`` character before and after the name.

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


class HierarchyArrayObject(HierarchyObjectBase[int], RangeableObjectMixin):
    """A simulation object that is an array of hierarchical simulation objects.

    This class is used for array-like hierarchical structures like "generate loops".

    Children of this object are found by supplying a numerical index using index syntax.
    For example, if you have a design with a generate loop ``gen_pipe_stages`` from the range ``0`` to ``7``:

    .. code-block:: python3

        block_0 = dut.gen_pipe_stages[0]
        block_7 = dut.gen_pipe_stages[7]

    Accessing a non-existent child results in an :class:`IndexError`.

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

    # ideally `__len__` could be implemented in terms of `range`, but `range` doesn't work universally.
    __len__ = HierarchyObjectBase.__len__

    def __iter__(self) -> Iterator[SimHandleBase]:
        # must use `sorted(self._keys())` instead of the range because `range` doesn't work universally.
        for i in sorted(self._keys()):
            yield self[i]


class _GPISetAction(enum.IntEnum):
    DEPOSIT = 0
    FORCE = 1
    RELEASE = 2


#: The type of the value a :class:`Deposit` or :class:`Force` action contains.
ValueT = TypeVar("ValueT")


class Deposit(Generic[ValueT]):
    """Action used for placing a value into a given handle. This is the default action.

    If another deposit comes after this deposit, the newer deposit overwrites the old value.
    If an HDL process is driving the signal/net/register where a deposit from cocotb is made,
    the deposited value will be overwritten at the end of the next delta cycle,
    essentially causing a single delta cycle "glitch" in the waveform.
    """

    def __init__(self, value: ValueT) -> None:
        self.value = value


class Force(Generic[ValueT]):
    r"""Action used to force a handle to a given value until a :class:`Release` is applied.

    :class:`Deposit` writes from cocotb or drives from HDL processes
    do not cause the value to change until the handle is :class:`Release`\ d.
    Further :class:`Force`\ s will overwrite the value and leave the value forced.
    :class:`Freeze`\ s will act as a no-op.
    """

    def __init__(self, value: ValueT) -> None:
        self.value = value


class Freeze:
    r"""Action used to make a handle keep its current value until a :class:`Release` is applied.

    :class:`Deposit` writes from cocotb or drives from HDL processes
    do not cause the value to change until the handle is :class:`Release`\ d.
    :class:`Force`\ s will overwrite the value and leave the value forced.
    Further :class:`Freeze`\ s will act as a no-op.
    """


class Release:
    """Action used to stop the effects of a previously applied :class:`Force`/:class:`Freeze` action."""


def _map_action_obj_to_value_action_enum_pair(
    handle: "ValueObjectBase[Any, Any]",
    value: Union[ValueT, Deposit[ValueT], Force[ValueT], Freeze, Release],
) -> Tuple[ValueT, _GPISetAction]:
    if isinstance(value, Deposit):
        return value.value, _GPISetAction.DEPOSIT
    elif isinstance(value, Force):
        return value.value, _GPISetAction.FORCE
    elif isinstance(value, Freeze):
        return handle.value, _GPISetAction.FORCE
    elif isinstance(value, Release):
        return handle.value, _GPISetAction.RELEASE
    else:
        return value, _GPISetAction.DEPOSIT


#: Type accepted and returned by the :attr:`~ValueObjectBase.value` property.
ValuePropertyT = TypeVar("ValuePropertyT")


#: Type accepted by :meth:`~ValueObjectBase.set` and :meth:`~ValueObjectBase.setimmediatevalue`.
ValueSetT = TypeVar("ValueSetT")


class ValueObjectBase(SimHandleBase, Generic[ValuePropertyT, ValueSetT]):
    """Base class for all simulation objects that have a value."""

    @property
    @abstractmethod
    def value(self) -> ValuePropertyT:
        """Get or set the value of the simulation object.

        :getter: Returns the current value of the simulation object.

        :setter:
            Assigns the value at end of the current simulator delta cycle.
            Takes whatever values that :meth:`set` takes,
            including :class:`Deposit`, :class:`Force`, :class:`Freeze`, and :class:`Release` actions.

        .. note::

            Use :meth:`setimmediatevalue` if you need to set the value of the simulation object immediately.
        """

    @value.setter
    @abstractmethod
    def value(self, value: ValuePropertyT) -> None: ...

    def set(
        self,
        value: Union[ValueSetT, Deposit[ValueSetT], Force[ValueSetT], Freeze, Release],
    ) -> None:
        """Assign the value to this simulation object at the end of the current delta cycle.

        This is known in Verilog as a "non-blocking assignment" and in VHDL as a "signal assignment".

        See :class:`Deposit`, :class:`Force`, :class:`Freeze`, and :class:`Release` for additional actions that can be taken when setting a value.
        The default behavior is to :class:`Deposit` the value.
        Use these actions like so:

        .. code-block:: python3

            dut.handle.set(1)  # default Deposit action
            dut.handle.set(Deposit(2))
            dut.handle.set(Force(3))
            dut.handle.set(Freeze())
            dut.handle.set(Release())
        """
        if self.is_const:
            raise TypeError(f"{self._path} is constant")

        value_, action = _map_action_obj_to_value_action_enum_pair(self, value)

        self._set_value(value_, action, _inertial_write)

    def setimmediatevalue(
        self,
        value: Union[ValueSetT, Deposit[ValueSetT], Force[ValueSetT], Freeze, Release],
    ) -> None:
        """Assign a value to this simulation object immediately.

        This is known in Verilog as a "blocking" assignment and in VHDL as a variable assignment.

        See :class:`Deposit`, :class:`Force`, :class:`Freeze`, and :class:`Release` for additional actions that can be taken when setting a value.
        The default behavior is to :class:`Deposit` the value.
        See :meth:`set` for an example on how to use these action types.
        """
        if self.is_const:
            raise TypeError(f"{self._path} is constant")

        value_, action = _map_action_obj_to_value_action_enum_pair(self, value)

        self._set_value(value_, action, _write_now)

    @cached_property
    def is_const(self) -> bool:
        """``True`` if the simulator object is immutable, e.g. a Verilog parameter or VHDL constant or generic."""
        return self._handle.get_const()

    @abstractmethod
    def _set_value(
        self,
        value: ValueSetT,
        action: _GPISetAction,
        schedule_write: Callable[
            ["ValueObjectBase[Any, Any]", Callable[..., None], Sequence[Any]], None
        ],
    ) -> None:
        """Schedule a write of the given value to a simulator object.

        Conversion from multiple Python types into a type understood by the simulator is expected.
        This is used to implement the :attr:`value` property setter, :meth:`setimmediatevalue`, and :meth:`set`.

        Args:
            value: A value used to set the handle.
            action: Whether to deposit, force, or release the value on the handle.
            schedule_write: A function which takes ``(handle, callback, args)`` to schedule the writes.
        """


#: Type of value of each element in an :class:`ArrayObject`.
ElemValueT = TypeVar("ElemValueT")

#: Subtype of :class:`ValueObjectBase` returned when iterating or indexing a :class:`ArrayObject`.
ChildObjectT = TypeVar("ChildObjectT", bound=ValueObjectBase[Any, Any])


class ArrayObject(
    ValueObjectBase[Array[ElemValueT], Array[ElemValueT]],
    RangeableObjectMixin,
    Generic[ElemValueT, ChildObjectT],
):
    """A simulation object that is an array of value-having simulation objects.

    This object is used whenever an array, that isn't a logic array or string, is seen.
    In Verilog, only unpacked vectors use this type.
    Packed vectors are typically mapped to :class:`LogicObject`.

    These objects can be iterated over to yield child objects:

    .. code-block:: python3

        for child in dut.array_object:
            print(child._path)

    A particular child can be retrieved using its index:

    .. code-block:: python3

        child = dut.array_object[0]

        # reversed iteration over children
        for child_idx in reversed(dut.array_object.range):
            dut.array_object[child_idx]

    """

    def __init__(self, handle: simulator.gpi_sim_hdl, path: Optional[str]) -> None:
        super().__init__(handle, path)
        self._sub_handles: Dict[int, ChildObjectT] = {}

    @property
    def value(self) -> Array[ElemValueT]:
        """The current value of the simulation object.

        :getter:
            Returns the current values of each element of the array object as an :class:`~cocotb.types.Array` of element values.
            The elements of the array appear in the list in left-to-right order.

        :setter:
            Assigns an :class:`~cocotb.types.Array`, :class:`list`, or :class:`tuple` of values to each element of the array at the end of the current delta cycle.
            The element values are assigned in left-to-right order.

        Given an HDL array ``arr``, when getting the value:

        +--------------+---------------------+--------------------------------------------------------------------------------------------------+
        | Verilog      | VHDL                | ``arr.value`` is equivalent to                                                                   |
        +==============+=====================+==================================================================================================+
        | ``arr[4:7]`` | ``arr(4 to 7)``     | ``Array([arr[4].value, arr[5].value, arr[6].value, arr[7].value], range=Range(4, 'to', 7))``     |
        +--------------+---------------------+--------------------------------------------------------------------------------------------------+
        | ``arr[7:4]`` | ``arr(7 downto 4)`` | ``Array([arr[7].value, arr[6].value, arr[5].value, arr[4].value], range=Range(7, 'downto', 4))`` |
        +--------------+---------------------+--------------------------------------------------------------------------------------------------+

        When setting the signal as in ``arr.value = ...``, the same index equivalence as noted in the table holds.

        .. warning::
            Assigning a value to a sub-handle:

            - **Wrong**: ``dut.some_array.value[0] = 1`` (gets value as a list then updates index 0)
            - **Correct**: ``dut.some_array[0].value = 1``

        Raises:
            TypeError:
                If assigning a type other than :class:`list`.

            ValueError:
                If assigning a :class:`list` of different length than the simulation object.
        """
        return Array((self[i].value for i in self.range), range=self.range)

    @value.setter
    def value(self, value: Array[ElemValueT]) -> None:
        self.set(value)

    def _set_value(
        self,
        value: Union[Array[ElemValueT], Sequence[ElemValueT]],
        action: _GPISetAction,
        schedule_write: Callable[
            [ValueObjectBase[Any, Any], Callable[..., None], Sequence[Any]], None
        ],
    ) -> None:
        if not isinstance(value, (collections.abc.Sequence, Array)):
            raise TypeError(
                f"Assigning non-list value to object {self._name} of type {type(self)}"
            )
        if len(value) != len(self):
            raise ValueError(
                "Assigning list of length %d to object %s of length %d"
                % (len(value), self._name, len(self))
            )
        for elem, self_idx in zip(value, self.range):
            self[self_idx]._set_value(elem, action, schedule_write)

    def __getitem__(self, index: int) -> ChildObjectT:
        if isinstance(index, slice):
            raise IndexError("Slice indexing is not supported")
        if index in self._sub_handles:
            return self._sub_handles[index]
        new_handle = self._handle.get_handle_by_index(index)
        if not new_handle:
            raise IndexError(f"{self._path} contains no object at index {index}")
        path = self._path + "[" + str(index) + "]"
        self._sub_handles[index] = cast(ChildObjectT, SimHandle(new_handle, path))
        return self._sub_handles[index]

    def __iter__(self) -> Iterable[ChildObjectT]:
        for i in self.range:
            yield self[i]


class LogicObject(
    ValueObjectBase[LogicArray, Union[LogicArray, Logic, int]],
    RangeableObjectMixin,
):
    """A logic or logic array simulation object.

    Verilog types that map to this object:
        * ``logic``
        * ``reg``
        * ``bit``
        * packed any-dimensional vectors of ``logic``, ``reg``, or ``bit``
        * packed any-dimensional vectors of packed structures

    VHDL types that map to this object:
        * ``std_logic`` and ``std_ulogic``
        * ``std_logic_vector`` and ``std_ulogic_vector``
        * ``unsigned``
        * ``signed``
        * ``ufixed``
        * ``sfixed``
        * ``float``
    """

    def __init__(self, handle: simulator.gpi_sim_hdl, path: Optional[str]) -> None:
        super().__init__(handle, path)

    def _set_value(
        self,
        value: Union[LogicArray, Logic, int, str],
        action: _GPISetAction,
        schedule_write: Callable[
            [ValueObjectBase[Any, Any], Callable[..., None], Sequence[Any]], None
        ],
    ) -> None:
        value_: LogicArray
        if isinstance(value, int):
            min_val, max_val = _value_limits(len(self), _Limits.VECTOR_NBIT)
            if min_val <= value <= max_val:
                if len(self) <= 32:
                    schedule_write(
                        self, self._handle.set_signal_val_int, (action, value)
                    )
                    return

                if value < 0:
                    value_ = LogicArray.from_signed(
                        value,
                        Range(len(self) - 1, "downto", 0),
                    )
                else:
                    value_ = LogicArray.from_unsigned(
                        value,
                        Range(len(self) - 1, "downto", 0),
                    )
            else:
                raise OverflowError(
                    f"Int value ({value!r}) out of range for assignment of {len(self)!r}-bit signal ({self._name!r})"
                )

        elif isinstance(value, str):
            value_ = LogicArray(value, self.range)

        elif isinstance(value, LogicArray):
            if len(self) != len(value):
                raise ValueError(
                    f"cannot assign value of length {len(value)} to handle of length {len(self)}"
                )
            value_ = value

        elif isinstance(value, Logic):
            if len(self) != 1:
                raise ValueError(
                    f"cannot assign value of length 1 to handle of length {len(self)}"
                )
            value_ = LogicArray([value])

        else:
            raise TypeError(
                f"Unsupported type for value assignment: {type(value)} ({value!r})"
            )

        schedule_write(self, self._handle.set_signal_val_binstr, (action, str(value_)))

    @property
    def value(self) -> LogicArray:
        """The value of the simulation object.

        :getter:
            Returns the current value of the simulation object as a :class:`~cocotb.types.LogicArray`,
            even when the object is a single logic object and not an array.

        :setter:
            Assigns a value at the end of the current delta cycle.
            A :class:`~cocotb.types.LogicArray`, :class:`str`, or :class:`int` can be used to set the value.
            When a :class:`str` or :class:`int` is given, it is as if it is first converted a :class:`~cocotb.types.LogicArray`.

        Raises:
            TypeError: If assignment is given a type other than :class:`~cocotb.types.LogicArray`, :class:`int`, or :class:`str`.

            OverflowError:
                If int value is out of the range that can be represented by the target:
                ``-2**(len(handle) - 1) <= value <= 2**len(handle) - 1``

        .. versionchanged:: 2.0
            Using :class:`ctypes.Structure` objects to set values was removed.
            Convert the struct object to a :class:`~cocotb.types.LogicArray` before assignment using
            ``LogicArray("".join(format(int(byte), "08b") for byte in bytes(struct_obj)))`` instead.

        .. versionchanged:: 2.0
            Using :class:`dict` objects to set values was removed.
            Convert the dictionary to an integer before assignment using
            ``sum(v << (d['bits'] * i) for i, v in enumerate(d['values']))`` instead.
        """
        binstr = self._handle.get_signal_val_binstr()
        return LogicArray(binstr)

    @value.setter
    def value(self, value: LogicArray) -> None:
        self.set(value)

    @deprecated(
        "`int(handle)` casts have been deprecated. Use `int(handle.value)` instead."
    )
    def __int__(self) -> int:
        return int(self.value)

    @deprecated(
        "`str(handle)` casts have been deprecated. Use `str(handle.value)` instead."
    )
    def __str__(self) -> str:
        return str(self.value)

    @lru_cache(maxsize=None)
    def __len__(self) -> int:
        # can't use `range` to get length because `range` is for outer-most dimension only
        # and this object needs to support multi-dimensional packed arrays.
        return self._handle.get_num_elems()


class RealObject(ValueObjectBase[float, float]):
    """A real/float simulation object.

    This type is used when a ``real`` object in VHDL or ``float`` object in Verilog is seen.
    """

    def __init__(self, handle: simulator.gpi_sim_hdl, path: Optional[str]) -> None:
        super().__init__(handle, path)

    def _set_value(
        self,
        value: float,
        action: _GPISetAction,
        schedule_write: Callable[
            [ValueObjectBase[Any, Any], Callable[..., None], Sequence[Any]], None
        ],
    ) -> None:
        if not isinstance(value, (float, int)):
            raise TypeError(
                f"Unsupported type for real value assignment: {type(value)} ({value!r})"
            )

        schedule_write(self, self._handle.set_signal_val_real, (action, value))

    @property
    def value(self) -> float:
        """The value of the simulation object.

        :getter:
            Returns the current value of the simulation object as a :class:`float`.

        :setter:
            Assigns a :class:`float` value at the end of the current delta cycle.

        Raises:
            TypeError: If assignment is given a type other than :class:`float`.
        """
        return self._handle.get_signal_val_real()

    @value.setter
    def value(self, value: float) -> None:
        self.set(value)

    @deprecated(
        "`float(handle)` casts have been deprecated. Use `float(handle.value)` instead."
    )
    def __float__(self) -> float:
        return self.value


class EnumObject(ValueObjectBase[int, int]):
    """An enumeration simulation object.

    This type is used when an enumerated-type simulation object is seen that isn't a "logic" or similar type.
    """

    def __init__(self, handle: simulator.gpi_sim_hdl, path: Optional[str]) -> None:
        super().__init__(handle, path)

    def _set_value(
        self,
        value: int,
        action: _GPISetAction,
        schedule_write: Callable[
            [ValueObjectBase[Any, Any], Callable[..., None], Sequence[Any]], None
        ],
    ) -> None:
        if not isinstance(value, int):
            raise TypeError(
                f"Unsupported type for enum value assignment: {type(value)} ({value!r})"
            )

        min_val, max_val = _value_limits(32, _Limits.UNSIGNED_NBIT)
        if min_val <= value <= max_val:
            schedule_write(self, self._handle.set_signal_val_int, (action, value))
        else:
            raise OverflowError(
                f"Int value ({value!r}) out of range for assignment of enum signal ({self._name!r})"
            )

    @property
    def value(self) -> int:
        """The value of the simulation object.

        :getter:
            Returns the current enumeration value of the simulation object as an :class:`int`.
            The value is the integer mapping of the enumeration value.

        :setter:
            Assigns a new enumeration value at the end of the current delta cycle using an :class:`int`.
            The :class:`int` value is the integer mapping of the enumeration value.

        Raises:
            TypeError: If assignment is given a type other than :class:`int`.

            OverflowError: If the value used in assignment is out of range of a 32-bit signed integer.
        """
        return self._handle.get_signal_val_long()

    @value.setter
    def value(self, value: int) -> None:
        self.set(value)

    @deprecated(
        "`int(handle)` casts have been deprecated. Use `int(handle.value)` instead."
    )
    def __int__(self) -> int:
        return int(self.value)


class IntegerObject(ValueObjectBase[int, int]):
    """An integer simulation object.

    Verilog types that map to this object:
        * ``byte``
        * ``shortint``
        * ``int``
        * ``longint``

    This type should not be used for the 4-state integer types ``integer`` and ``time``.

    VHDL types that map to this object:
        * ``integer``
        * ``natural``
        * ``positive``

    Objects that use this type are assumed to be two's complement 32-bit integers with 2-state (``0`` and ``1``) bits.
    """

    def __init__(self, handle: simulator.gpi_sim_hdl, path: Optional[str]) -> None:
        super().__init__(handle, path)

    def _set_value(
        self,
        value: int,
        action: _GPISetAction,
        schedule_write: Callable[
            [ValueObjectBase[Any, Any], Callable[..., None], Sequence[Any]], None
        ],
    ) -> None:
        if not isinstance(value, int):
            raise TypeError(
                f"Unsupported type for integer value assignment: {type(value)} ({value!r})"
            )

        min_val, max_val = _value_limits(32, _Limits.SIGNED_NBIT)
        if min_val <= value <= max_val:
            schedule_write(self, self._handle.set_signal_val_int, (action, value))
        else:
            raise OverflowError(
                f"Int value ({value!r}) out of range for assignment of integer signal ({self._name!r})"
            )

    @property
    def value(self) -> int:
        """The value of the simulation object.

        :getter:
            Returns the current value of the simulation object as a :class:`int`.

        :setter:
            Assigns a :class:`int` value at the end of the current delta cycle.

        Raises:
            TypeError: If assignment is given a type other than :class:`int`.

            OverflowError: If the value used in assignment is out of range of a 32-bit signed integer.
        """
        return self._handle.get_signal_val_long()

    @value.setter
    def value(self, value: int) -> None:
        self.set(value)

    @deprecated(
        "`int(handle)` casts have been deprecated. Use `int(handle.value)` instead."
    )
    def __int__(self) -> int:
        return self.value


class StringObject(
    ValueObjectBase[bytes, bytes],
    RangeableObjectMixin,
):
    """A string simulation object.

    This type is used when a ``string`` (VHDL or Verilog) simulation object is seen.
    """

    def __init__(self, handle: simulator.gpi_sim_hdl, path: Optional[str]) -> None:
        super().__init__(handle, path)

    def _set_value(
        self,
        value: bytes,
        action: _GPISetAction,
        schedule_write: Callable[
            [ValueObjectBase[Any, Any], Callable[..., None], Sequence[Any]], None
        ],
    ) -> None:
        if not isinstance(value, bytes):
            raise TypeError(
                f"Unsupported type for string value assignment: {type(value)} ({value!r})"
            )

        schedule_write(self, self._handle.set_signal_val_str, (action, value))

    @property
    def value(self) -> bytes:
        """The value of the simulation object.

        :getter:
            Returns the current value of the simulation object as a :class:`bytes`.

        :setter:
            Assigns a :class:`bytes` value at the end of the current delta cycle.
            When the value's length is less than the simulation object's,
            the value is padded with NUL (``'\0'``) characters up to the appropriate length.
            When the value's length is greater than the simulation object's,
            the value is truncated without a NUL terminator to the appropriate length,
            without warning.

        Strings in both Verilog and VHDL are byte arrays without any particular encoding.
        Encoding must be done to turn Python strings into byte arrays.
        Because :ref:`there are many encodings <https://docs.python.org/3/library/codecs.html#standard-encodings>`,
        this step is left up to the user.

        An example of how encoding and decoding could be accomplished using an ASCII string.

        .. code-block:: python3

            # lowercase a string
            value = dut.string_handle.value.decode("ascii")
            value = value.lower()
            dut.string_handle.value = value.encode("ascii")

        Raises:
            TypeError: If assignment is given a type other than :class:`bytes`.

        .. versionchanged:: 1.4
            Takes :class:`bytes` instead of :class:`str`.
            Users are now expected to choose an encoding when using these objects.
        """
        return self._handle.get_signal_val_str()

    @value.setter
    def value(self, value: bytes) -> None:
        self.set(value)

    @deprecated(
        '`str(handle)` casts have been deprecated. Use `handle.value.decode("ascii")` instead.'
    )
    def __str__(self) -> str:
        return self.value.decode("ascii")


_ConcreteHandleTypes = Union[
    HierarchyObject,
    HierarchyArrayObject,
    LogicObject,
    ArrayObject[Any, ValueObjectBase[Any, Any]],
    RealObject,
    IntegerObject,
    EnumObject,
    StringObject,
]


_handle2obj: Dict[
    simulator.gpi_sim_hdl,
    _ConcreteHandleTypes,
] = {}

_type2cls: Dict[int, Type[_ConcreteHandleTypes]] = {
    simulator.MODULE: HierarchyObject,
    simulator.STRUCTURE: HierarchyObject,
    simulator.PACKED_STRUCTURE: LogicObject,
    simulator.REG: LogicObject,
    simulator.NET: LogicObject,
    simulator.NETARRAY: ArrayObject[Any, ValueObjectBase[Any, Any]],
    simulator.REAL: RealObject,
    simulator.INTEGER: IntegerObject,
    simulator.ENUM: EnumObject,
    simulator.STRING: StringObject,
    simulator.GENARRAY: HierarchyArrayObject,
    simulator.PACKAGE: HierarchyObject,
}


def SimHandle(
    handle: simulator.gpi_sim_hdl, path: Optional[str] = None
) -> SimHandleBase:
    """Factory function to create the correct type of `SimHandle` object.

    Args:
        handle: The GPI handle to the simulator object.
        path: Path to this handle.

    Returns:
        An appropriate :class:`SimHandleBase` object.

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
            f"Couldn't find a matching object for GPI type {handle.get_type_string()}({t}) (path={path})"
        )
    obj = _type2cls[t](handle, path)
    _handle2obj[handle] = obj
    return obj
