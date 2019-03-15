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

"""Common bus related functionality.
A bus is simply defined as a collection of signals.
"""
from cocotb.handle import AssignmentResult

def _build_sig_attr_dict(signals):
    if isinstance(signals, dict):
        return signals
    else:
        sig_to_attr = {}
        for sig in signals:
            sig_to_attr[sig] = sig
        return sig_to_attr


class Bus(object):
    """Wraps up a collection of signals.

    Assumes we have a set of signals/nets named ``entity.<bus_name><separator><signal>``.

    For example a bus ``stream_in`` with signals ``valid`` and ``data`` is assumed
    to be named ``dut.stream_in_valid`` and ``dut.stream_in_data`` (with 
    the default separator '_').

    TODO:
        Support for struct/record ports where signals are member names.
    """
    def __init__(self, entity, name, signals, optional_signals=[], bus_separator="_", array_idx=None):
        """Args:
            entity (SimHandle): SimHandle instance to the entity containing the bus.
            name (str): Name of the bus. ``None`` for nameless bus, e.g. bus-signals
                in an interface or a modport (untested on struct/record, 
                but could work here as well).
            signals (list/dict): In the case of an obj (passed to drive/capture) that
                has the same attribute names as the signal names of the bus,
                the signals argument can be a list of those names.
                When obj has different attribute names, the signals arg should be
                a dict that maps bus attribute names to obj signal names.
            optional_signals (list/dict, optional): Signals that don't have to be present
                on the interface. 
                See ``signals`` argument above for details.
            bus_separator (str, optional): Character(s) to use as separator between bus
                name and signal name. Defaults to '_'.
            array_idx (int or None, optional): Optional index when signal is an array.
        """
        self._entity = entity
        self._name = name
        self._signals = {}

        for attr_name, sig_name in _build_sig_attr_dict(signals).items():
            if name:
                signame = name + bus_separator + sig_name
            else:
                signame = sig_name

            if array_idx is not None:
                signame += "[{:d}]".format(array_idx)
            self._add_signal(attr_name, signame)

        # Also support a set of optional signals that don't have to be present
        for attr_name, sig_name in _build_sig_attr_dict(optional_signals).items():
            if name:
                signame = name + bus_separator + sig_name
            else:
                signame = sig_name

            if array_idx is not None:
                signame += "[{:d}]".format(array_idx)

            self._entity._log.debug("Signal name {}".format(signame))
            # Attempts to access a signal that doesn't exist will print a
            # backtrace so we 'peek' first, slightly un-pythonic
            if entity.__hasattr__(signame):
                self._add_signal(attr_name, signame)
            else:
                self._entity._log.debug("Ignoring optional missing signal "
                                        "%s on bus %s" % (sig_name, name))

    def _add_signal(self, attr_name, signame):
        self._entity._log.debug("Signal name {}".format(signame))
        setattr(self, attr_name, getattr(self._entity, signame))
        self._signals[attr_name] = getattr(self, attr_name)

    def drive(self, obj, strict=False):
        """Drives values onto the bus.

        Args:
            obj: Object with attribute names that match the bus signals.
            strict (bool, optional): Check that all signals are being assigned.

        Raises:
            AttributeError: If not all signals have been assigned when ``strict=True``.
        """
        for attr_name, hdl in self._signals.items():
            if not hasattr(obj, attr_name):
                if strict:
                    msg = ("Unable to drive onto {0}.{1} because {2} is missing "
                           "attribute {3}".format(self._entity._name,
                                                  self._name,
                                                  obj.__class__.__name__,
                                                  attr_name))
                    raise AttributeError(msg)
                else:
                    continue
            val = getattr(obj, attr_name)
            hdl <= val

    def capture(self):
        """Capture the values from the bus, returning an object representing the capture.

        Returns:
            dict: A dictionary that supports access by attribute, 
            where each attribute corresponds to each signal's value.
        Raises:
            RuntimeError: If signal not present in bus,
                or attempt to modify a bus capture.
        """
        class _Capture(dict):
            def __getattr__(self, name):
                if name in self:
                    return self[name]
                else:
                    raise RuntimeError('Signal {} not present in bus'.format(name))

            def __setattr__(self, name, value):
                raise RuntimeError('Modifying a bus capture is not supported')

            def __delattr__(self, name):
                raise RuntimeError('Modifying a bus capture is not supported')

        _capture = _Capture()
        for attr_name, hdl in self._signals.items():
            _capture[attr_name] = hdl.value

        return _capture

    def sample(self, obj, strict=False):
        """Sample the values from the bus, assigning them to *obj*.

        Args:
            obj: Object with attribute names that match the bus signals.
            strict (bool, optional): Check that all signals being sampled
                are present in *obj*.

        Raises:
            AttributeError: If attribute is missing in *obj* when ``strict=True``.
        """
        for attr_name, hdl in self._signals.items():
            if not hasattr(obj, attr_name):
                if strict:
                    msg = ("Unable to sample from {0}.{1} because {2} is missing "
                           "attribute {3}".format(self._entity._name,
                                                  self._name,
                                                  obj.__class__.__name__,
                                                  attr_name))
                    raise AttributeError(msg)
                else:
                    continue
            # Try to use the get/set_binstr methods because they will not clobber the properties
            # of obj.attr_name on assignment.  Otherwise use setattr() to crush whatever type of
            # object was in obj.attr_name with hdl.value:
            try:
                getattr(obj, attr_name).set_binstr(hdl.value.get_binstr())
            except AttributeError:
                setattr(obj, attr_name, hdl.value)

    def __le__(self, value):
        """Overload the less than or equal to operator for value assignment"""
        self.drive(value)
        return AssignmentResult(self, value)
