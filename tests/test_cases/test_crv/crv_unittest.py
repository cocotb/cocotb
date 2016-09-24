
'''Copyright (c) 2016, Marek Cieplucha, https://github.com/mciepluc
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met (The BSD 2-Clause 
License):

1. Redistributions of source code must retain the above copyright notice, 
this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, 
this list of conditions and the following disclaimer in the documentation and/or 
other materials provided with the distribution.

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

"""
Constrained-random verification features unittest.
"""
import cocotb
from cocotb import crv
from cocotb import coverage

import unittest

class TestCRV(unittest.TestCase):

    class SimpleRandomized(crv.Randomized):

        def __init__(self, x, y):
            crv.Randomized.__init__(self)
            self.x = x
            self.y = y
            self.size = "small"

            self.addRand("x", list(range(0, 10)))
            self.addRand("y", list(range(0, 10)))
            self.addRand("size", ["small", "medium", "large"])

            self.addConstraint(lambda x, y: x < y)

    def test_simple_0(self):
        print("Running test_simple_0")
        size_hits = []
        for _ in range(10):
            a = self.SimpleRandomized(0, 0)
            a.randomize()
            self.assertTrue(a.x < a.y)
            size_hits.append(a.size)
        self.assertTrue(
            [x in size_hits for x in["small", "medium", "large"]] ==
            [True, True, True]
        )

    class RandomizedTrasaction(crv.Randomized):

        def __init__(self, address, data=0, write=False, delay=1):
            crv.Randomized.__init__(self)
            self.addr = address
            self.data = data
            self.write = write
            self.delay1 = delay
            self.delay2 = 0
            self.delay3 = 0

            if data is None:
                self.addRand("data")

            self.addRand("delay1", list(range(10)))
            self.addRand("delay2", list(range(10)))
            self.addRand("delay3", list(range(10)))
            
            c1 = lambda delay1, delay2: delay1 <= delay2
            d1 = lambda delay1, delay2: 0.9 if (delay2 < 5) else 0.1
            d2 = lambda addr, delay1: 0.5 * delay1 if (addr == 5) else 1
            d3 = lambda delay1: 0.7 if (delay1 < 5) else 0.3
            c2 = lambda addr, data: data < 10000 if (addr == 0) else data < 5000
            
            self.addConstraint(c1)
            self.addConstraint(c2)
            self.addConstraint(d1)
            self.addConstraint(d2)
            self.addConstraint(d3)

    def test_simple_1(self):
        print("Running test_simple_1")
        for i in range(10):
            x = self.RandomizedTrasaction(i, data=None)
            x.randomize()
            self.assertTrue(x.delay1 <= x.delay2)
            self.assertTrue(x.data <= 10000)
            print("delay1 = %d, delay2 = %d, delay3 = %d, data = %d" %
                  (x.delay1, x.delay2, x.delay3, x.data))

    def test_randomize_with(self):
        print("Running test_randomize_with")
        for i in range(10):
            x = self.RandomizedTrasaction(i, data=None)
            x.randomize_with(lambda delay1, delay2: delay1 == delay2 - 1)
            print("delay1 = %d, delay2 = %d, delay3 = %d, data = %d" %
                  (x.delay1, x.delay2, x.delay3, x.data))
            self.assertTrue((x.delay2 - x.delay1) == 1)
            self.assertTrue(x.data <= 10000)

    def test_adding_constraints(self):
        print("Running test_adding_constraints")

        c3 = lambda data, delay1: 0 if (data < 10) else 1
        c4 = lambda data, delay3: 0.5 * delay3 if (data < 20) else 2 * delay3
        c5 = lambda data: data < 50

        for i in range(5):
            x = self.RandomizedTrasaction(i, data=None)
            x.addConstraint(c3)
            x.addConstraint(c4)
            x.addConstraint(c5)
            x.randomize()
            print("delay1 = %d, delay2 = %d, delay3 = %d, data = %d" %
                  (x.delay1, x.delay2, x.delay3, x.data))
            self.assertTrue(x.delay1 <= x.delay2)
            self.assertTrue(x.data < 50)  # added such new constraint
            # added distribution with 0 probability
            self.assertTrue(x.data > 10)

    def test_deleting_constraints(self):
        print("Running test_deleting_constraints")

        c3 = lambda data: data < 50

        for i in range(5):
            x = self.RandomizedTrasaction(i, data=None)
            x.addConstraint(c3)
            x.randomize()
            print("delay1 = %d, delay2 = %d, delay3 = %d, data = %d" %
                  (x.delay1, x.delay2, x.delay3, x.data))
            self.assertTrue(x.delay1 <= x.delay2)
            self.assertTrue(x.data < 50)
            x.delConstraint(c3)
            x.randomize()
            print("delay1 = %d, delay2 = %d, delay3 = %d, data = %d" %
                  (x.delay1, x.delay2, x.delay3, x.data))
            self.assertTrue(x.delay1 <= x.delay2)
            self.assertTrue(x.data > 50)
            
    def test_solve_order(self):
        print("Running test_solve_order")

        for i in range(10):
            x = self.RandomizedTrasaction(i, data=None)
            x.solveOrder("delay1", ["delay2", "delay3"])
            x.randomize()
            print("delay1 = %d, delay2 = %d, delay3 = %d, data = %d" %
                  (x.delay1, x.delay2, x.delay3, x.data))
            self.assertTrue(x.delay1 <= x.delay2) 
            
    def test_cannot_resolve(self):
        print("Running test_cannot_resolve")

        c3 = lambda delay2, delay3: delay3 > delay2
        c4 = lambda delay1: delay1 == 9

        for i in range(10):
            x = self.RandomizedTrasaction(i, data=None)
            x.addConstraint(c3)
            x.addConstraint(c4)
            try:
                x.randomize()
                self.assertTrue(0) 
            except Exception:
                self.assertTrue(1)     
                
    def test_zero_probability(self):
        print("Running test_cannot_resolve")

        d4 = lambda delay2: 0 if delay2 < 10 else 1

        for i in range(10):
            x = self.RandomizedTrasaction(i, data=None)
            x.addConstraint(d4)
            x.randomize()
            print("delay1 = %d, delay2 = %d, delay3 = %d, data = %d" %
                  (x.delay1, x.delay2, x.delay3, x.data))  
            self.assertTrue(x.delay2 == 0) 

    class RandomizedDist(crv.Randomized):

        def __init__(self, limit, n):
            crv.Randomized.__init__(self)
            self.x = 0
            self.y = 0
            self.z = 0
            self.n = n
            self.e_pr = False

            self.addRand("x", list(range(limit)))
            self.addRand("y", list(range(limit)))
            self.addRand("z", list(range(limit)))
            
        def post_randomize(self):
            if self.e_pr:
                self.n = self.x + self.y + self.z + self.n

    def test_distributions_1(self):
        print("Running test_distributions_1")

        d1 = lambda x: 20 / (x + 1)
        d2 = lambda y: 2 * y
        d3 = lambda n, z: n * z

        x_gr_y = 0

        for i in range(1, 10):
            foo = self.RandomizedDist(limit=20 * i, n=i - 1)
            foo.addConstraint(d1)
            foo.addConstraint(d2)
            foo.addConstraint(d3)
            foo.randomize()
            print("x = %d, y = %d, z = %d, n = %d" %
                  (foo.x, foo.y, foo.z, foo.n))
            x_gr_y = x_gr_y + 1 if (foo.x > foo.y) else x_gr_y - 1
            if (i == 1):
                # z should not be randomised as has 0 probability for each
                # solution
                self.assertTrue(foo.z == 0)

        # x should be less than y most of the time due to decreasing
        # distribution
        self.assertTrue(x_gr_y < 0)

    def test_cover(self):
        print("Running test_cover")
        n = 5

        cover = coverage.coverageSection(
            coverage.CoverPoint(
                "top.c1", xf=lambda x: x.x, bins=list(range(10))),
            coverage.CoverPoint(
                "top.c2", xf=lambda x: x.y, bins=list(range(10))),
            coverage.CoverCheck("top.check", f_fail=lambda x: x.n != n)
        )

        @cover
        def sample(x):
            print("x = %d, y = %d, z = %d, n = %d" %
                  (foo.x, foo.y, foo.z, foo.n))

        for _ in range(10):
            foo = self.RandomizedDist(10, n)
            foo.randomize()
            sample(foo)

        coverage_size = coverage.coverage_db["top"].size
        coverage_level = coverage.coverage_db["top"].coverage

        self.assertTrue(coverage_level > coverage_size / 2)  # expect >50%
        
    def test_post_randomize(self):
        print("Running test_post_randomize")

        n = 5
        foo = self.RandomizedDist(10, n)
        foo.e_pr = True #enable post-randomize
        for _ in range(5):
            foo.randomize()
            print("x = %d, y = %d, z = %d, n = %d" %
                  (foo.x, foo.y, foo.z, foo.n))
            
        self.assertTrue(foo.n > 5)

if __name__ == '__main__':
    unittest.main()
    #suite = unittest.TestSuite()
    #suite.addTest(TestCRV('test_cover'))
    #unittest.TextTestRunner().run(suite)

