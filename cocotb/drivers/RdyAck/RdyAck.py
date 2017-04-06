# Copyright 2016 Yu Sheng Lin
# This file is part of Cocotb.

import cocotb
import random
from cocotb.decorators import coroutine
from cocotb.triggers import RisingEdge, ReadOnly, Timer
from cocotb.drivers import BusDriver, ValidatedBusDriver
from cocotb.binary import BinaryValue
from cocotb.result import ReturnValue, TestError
from cocotb.bus import Bus
from cocotb.monitors import BusMonitor
from cocotb.handle import ModifiableObject
from itertools import izip

@cocotb.coroutine
def TimeoutTimer(t):
	yield Timer(t)
	raise TestError("Simulation too long, abort.")

class BusValue:
	"""A collection of BinaryValue"""
	def __init__(self, bus, signals, fill=None):
		self.signal_and_shapes = [(signal,) + self.get_shape(getattr(bus, signal)) for signal in signals]
		for name, shape, bitlen in self.signal_and_shapes:
			filll = fill*bitlen if fill else None
			signal = getattr(bus, name)
			if len(shape) == 0:
				binstr = filll if filll else signal.value.binstr
				value = BinaryValue(bits=bitlen, bigEndian=False, value=binstr)
			elif len(shape) == 1:
				value = list()
				for i in range(shape[0]):
					binstr = filll if filll else signal[i].value.binstr
					value.append(BinaryValue(bits=bitlen, bigEndian=False, value=binstr))
			elif len(shape) == 2:
				value = list()
				for i in range(shape[0]):
					valuei = list()
					signali = signal[i]
					for j in range(shape[1]):
						binstr = filll if filll else signali[j].value.binstr
						valuei.append(BinaryValue(bits=bitlen, bigEndian=False, value=binstr))
					value.append(valuei)
			setattr(self, name, value)

	@staticmethod
	def get_shape(signal):
		shape = list()
		while not isinstance(signal, ModifiableObject):
			shape.append(len(signal))
			signal = signal[0]
		assert len(shape) < 3, "Sorry, 3D+ array is not supported"
		return shape, len(signal)

	@staticmethod
	def convert_value(sig, shape):
		if len(shape) == 0:
			return sig.value
		elif len(shape) == 1:
			return [sig[i].value for i in range(shape[0])]
		elif len(shape) == 2:
			return [[sig[i][j].value for j in range(shape[1])] for i in range(shape[0])]

	def __str__(self):
		return str(self.value_tuple)

	@property
	def value_tuple(self):
		return tuple(self.convert_value(getattr(self, name), shape) for name, shape, bitlen in self.signal_and_shapes)

class HasBusValue:
	def __init__(self, entity, data_name):
		self.data_bus = Bus(entity, '', data_name)
		self.data_name = data_name
		self.X = self.create_data()
		self.assign_bus(self.X)

	def assign_bus(self, data):
		for name, shape, bitlen in data.signal_and_shapes:
			signal = getattr(self.data_bus, name)
			value = getattr(data, name)
			if len(shape) == 0:
				signal <= value
			elif len(shape) == 1:
				for i in range(shape[0]):
					signal[i] <= value[i]
			elif len(shape) == 2:
				for i in range(shape[0]):
					signali = signal[i]
					valuei = value[i]
					for j in range(shape[1]):
						signali[j] <= valuei[j]

	def create_data(self):
		return BusValue(self.data_bus, self.data_name, 'x')

_rdyack_name  = ['rdy', 'ack']
_val_name = ['dval']

class RdyAckMaster(BusDriver, HasBusValue):
	_signals = _rdyack_name
	def __init__(self, entity, name, clock, data_name):
		BusDriver.__init__(self, entity, name, clock)
		HasBusValue.__init__(self, entity, data_name)
		self.bus.rdy.setimmediatevalue(0)

	@coroutine
	def send(self, data, latency=0, sync=True):
		"""Send a tranaction. TODO: this is not re-entryable."""
		clk_edge = RisingEdge(self.clock)
		if sync:
			yield clk_edge
		for i in range(latency):
			yield clk_edge
		self.bus.rdy <= 1
		self.assign_bus(data)
		yield self._wait_for_signal(self.bus.ack)
		yield clk_edge
		self.bus.rdy <= 0
		self.assign_bus(self.X)

class RdyAckSlave(BusDriver):
	_signals = _rdyack_name
	def __init__(self, entity, name, clock, randmax):
		BusDriver.__init__(self, entity, name, clock)
		self.bus.ack.setimmediatevalue(0)
		self.randmax = randmax
		self.coro = cocotb.fork(self.respond())

	@cocotb.coroutine
	def respond(self):
		clk_edge = RisingEdge(self.clock)
		while True:
			yield clk_edge
			if self.bus.rdy.value:
				self.bus.ack <= 0
				for i in range(random.randint(0, self.randmax)):
					yield clk_edge
				self.bus.ack <= 1
				yield clk_edge
				self.bus.ack <= 0

class ValidMaster(BusDriver, HasBusValue):
	_signals = _val_name
	def __init__(self, entity, name, clock, data_name):
		BusDriver.__init__(self, entity, name, clock)
		HasBusValue.__init__(self, entity, data_name)
		self.bus.dval.setimmediatevalue(0)

	@coroutine
	def send(self, data, latency=0, sync=True):
		"""Send a tranaction. TODO: this is not re-entryable."""
		clk_edge = RisingEdge(self.clock)
		if sync:
			yield clk_edge
		for i in range(latency):
			yield clk_edge
		self.bus.dval <= 1
		self.assign_bus(data)
		yield clk_edge
		self.bus.dval <= 0
		self.assign_bus(self.X)

class ControlledMonitor(BusMonitor, HasBusValue):
	def __init__(self, entity, name, clock, data_name, collector, **kwargs):
		BusMonitor.__init__(self, entity, name, clock, **kwargs)
		HasBusValue.__init__(self, entity, data_name)
		self.collector = collector

	@cocotb.coroutine
	def _monitor_recv(self):
		clkedge = RisingEdge(self.clock)
		rdonly = ReadOnly()
		while True:
			yield clkedge
			yield rdonly
			if self.bus_ok():
				bus_value = BusValue(self.data_bus, self.data_name).value_tuple
				if self.collector is None:
					self._recv(bus_value)
				else:
					ret = self.collector(bus_value)
					if not ret is None:
						self._recv(ret)

	def bus_ok(self):
		return False

class RdyAckMonitor(ControlledMonitor):
	_signals = _rdyack_name
	def __init__(self, entity, name, clock, data_name, collector=None, **kwargs):
		ControlledMonitor.__init__(self, entity, name, clock, data_name, collector, **kwargs)

	def bus_ok(self):
		return self.bus.rdy.value and self.bus.ack.value

class ValidMonitor(ControlledMonitor):
	_signals = _val_name
	def __init__(self, entity, name, clock, data_name, collector=None, **kwargs):
		ControlledMonitor.__init__(self, entity, name, clock, data_name, collector, **kwargs)

	def bus_ok(self):
		return self.bus.dval.value
