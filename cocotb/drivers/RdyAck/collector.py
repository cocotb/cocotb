# Copyright 2016 Yu Sheng Lin
# This file is part of Cocotb.

import numpy as np
from itertools import izip

class CompareWrap(object):
	def __init__(self, iterable, verbose=False):
		self.iterable = iterable
		self.verbose = verbose

	def __eq__(self, rhs):
		"""
			Cocotb use __eq__ to check in expected_output then use __eq__ to check again
			So currently we just return true since we don't use reorder buffer
		"""
		return True

	def __ne__(self, rhs):
		if len(rhs.iterable) != len(self.iterable):
			return True
		for l, r in izip(self.iterable, rhs.iterable):
			if isinstance(l, np.ndarray) and isinstance(r, np.ndarray):
				eq = np.array_equal(l, r)
			else:
				eq = l == r
			if not eq:
				if self.verbose or rhs.verbose:
					print "Compare fail"
					print l
					print r
				return True
		return False

class VectorCollector(object):
	def __init__(self, shapes, n=0):
		self.shapes = shapes
		self.alloc(n)
		self.n = n
		self.i = 0

	def __call__(self, sigs):
		for sig_i, sig in enumerate(sigs):
			self.v[sig_i][self.i] = sig
		self.i += 1
		if self.i == self.n:
			self.i = 0
			return CompareWrap([v[:self.n] for v in self.v])
		return None

	def update(self, n, force=False):
		assert self.clean, "There are still {} data".format(self.i)
		if n == self.n if force else n > self.n:
			self.alloc(n)
		self.n = n

	def alloc(self, n):
		if n == 0:
			return
		v = list()
		for shape in self.shapes:
			lshape = [n]
			lshape.extend(shape)
			v.append(np.empty(lshape, dtype='i4'))
		self.v = v

	@property
	def clean(self):
		return self.i == 0

