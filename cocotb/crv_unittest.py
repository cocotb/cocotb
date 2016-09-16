
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
Contrained-random verification features.

Classes:
Randomized - base class for objects intended to have random variables
"""

import unittest
import crv


class TestCRV(unittest.TestCase):
    
    class SimpleRandomized(crv.Randomized):
        def __init__(self, x, y):
            crv.Randomized.__init__(self)
            self.x = 0
            self.y = 0
        
            self.addRand("x", range(0,10))
            self.addRand("y", range(0,10))
            
            self.addConstraint(lambda x, y : x < y)

    def test_simple_0(self):
        print "Running test_simple_0"
        results = []
        
        for i in range (10):
            a = self.SimpleRandomized(0,0)
            a.randomize();
            self.assertTrue(a.x < a.y)
        
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
                
            self.addRand("delay1", range(10))
            self.addRand("delay2", range(10))
            self.addRand("delay3", range(10))
            self.addConstraint(lambda delay1, delay2 : delay1 < delay2)
            self.addConstraint(lambda delay1, delay2 : 0.9 if (delay2 < 5) else 0.1)
            self.addConstraint(lambda delay1 : 0.7 if (delay1 < 5) else 0.3)
            self.addConstraint(lambda addr, delay1 : 0.5*delay1 if (addr == 5) else 1)
            self.addConstraint(lambda addr, data : data <= 10000 if (addr == 0) else data <= 5000)
            
    def test_simple_1(self):
        print "Running test_simple_1"
        for i in range(10):
            x = self.RandomizedTrasaction(i, data=None)
            x.randomize()
            self.assertTrue(x.delay1 < x.delay2)
            self.assertTrue(x.data <= 10000)
            print "delay1 = %d, delay2 = %d, delay3 = %d, data = %d" % (x.delay1, x.delay2, x.delay3, x.data)
            
    def test_randomize_with(self): 
        print "Running test_randomize_with"
        for i in range(10):
            x = self.RandomizedTrasaction(i, data=None)
            x.randomize_with(lambda delay1, delay2: delay1 == delay2 - 1)
            print "delay1 = %d, delay2 = %d, delay3 = %d, data = %d" % (x.delay1, x.delay2, x.delay3, x.data)
            self.assertTrue((x.delay2 - x.delay1) == 1)
            self.assertTrue(x.data <= 10000)
            
    def test_adding_constraints(self): 
        print "Running test_adding_constraints"
            
        c1 = lambda data, delay1 : 0 if (data < 10) else 1
        c2 = lambda data, delay3 : 0.5*delay3 if (data < 20) else 2*delay3
        c3 = lambda data : data < 50
        
        for i in range(5):
            x = self.RandomizedTrasaction(i, data=None)
            x.addConstraint(c1)
            x.addConstraint(c2)
            x.addConstraint(c3)
            x.randomize()
            print "delay1 = %d, delay2 = %d, delay3 = %d, data = %d" % (x.delay1, x.delay2, x.delay3, x.data)
            self.assertTrue(x.delay1 < x.delay2)
            self.assertTrue(x.data < 50) #added such new constraint
            self.assertTrue(x.data > 10) #added distribution with 0 probability
            
    def test_deleting_constraints(self): 
        print "Running test_deleting_constraints"
            
        c3 = lambda data : data < 50
        
        for i in range(5):
            x = self.RandomizedTrasaction(i, data=None)
            x.addConstraint(c3)
            x.randomize()
            print "delay1 = %d, delay2 = %d, delay3 = %d, data = %d" % (x.delay1, x.delay2, x.delay3, x.data)
            self.assertTrue(x.delay1 < x.delay2)
            self.assertTrue(x.data < 50) 
            x.delConstraint(c3)
            x.randomize()
            print "delay1 = %d, delay2 = %d, delay3 = %d, data = %d" % (x.delay1, x.delay2, x.delay3, x.data)
            self.assertTrue(x.delay1 < x.delay2)
            self.assertTrue(x.data > 50)
            
    class RandomizedDist(crv.Randomized):
        def __init__(self, limit, n):
            crv.Randomized.__init__(self)
            self.x = 0
            self.y = 0
            self.z = 0
            self.n = n

            self.addRand("x", range(limit))
            self.addRand("y", range(limit))
            self.addRand("z", range(limit))
            
    def test_distributions_1(self): 
        print "Running test_distributions_1"
            
        d1 = lambda x: 20/(x+1)
        d2 = lambda y: 2*y
        d3 = lambda n, z: n*z
        
        x_gr_y = 0
        
        for i in range(1,10):
            foo = self.RandomizedDist(limit=20*i, n=i-1)
            foo.addConstraint(d1)
            foo.addConstraint(d2)
            foo.addConstraint(d3)
            foo.randomize()
            print "x = %d, y = %d, z = %d, n = %d" % (foo.x, foo.y, foo.z, foo.n)
            x_gr_y = x_gr_y + 1 if (foo.x > foo.y) else x_gr_y - 1
            if (i==1):
                self.assertTrue(foo.z==0) #z should not be randomised as has 0 probability for each solution
        
        self.assertTrue(x_gr_y < 0) #x should be less than y most of the time due to decreasing distribution

if __name__ == '__main__':
    unittest.main()
