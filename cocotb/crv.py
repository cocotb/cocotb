
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

import random
import constraint
import inspect
import copy

class Randomized(object):

    def __init__(self):
        self._problem = constraint.Problem()
        self._randVariables = {}
    
    def addRand(self, var, domain):
        self._randVariables[var] = domain #add variable to the map
        self._problem.addVariable(var, domain)
    
    def addConstraint(self, constraint):
        variables = inspect.getargspec(constraint).args
        self._problem.addConstraint(constraint, variables)
        
    def pre_randomize(self):
        pass
    
    def post_randomize(self):
        pass
        
    def randomize(self, *constraints):
        """
        Randomizes a final class using predefined constraints + optional
        constraints given in an argument.
        """
        problem = copy.copy(self._problem)            
        self.pre_randomize()
        for cstr in constraints:
            variables = inspect.getargspec(cstr).args
            problem.addConstraint(cstr, variables)
        solutions = problem.getSolutions()
        solution = solutions[random.randint(0,len(solutions)-1)]
        for var in self._randVariables:
            setattr(self, var, solution[var]) 
        self.post_randomize()
        
    def randomize_with(self, *constraints):
        """
        Randomizes a final class using only constraints given in an argument.
        """
        problem = constraint.Problem() 
        for var in self._randVariables:
            problem.addVariable(var, self._randVariables[var])    
        for cstr in constraints:
            variables = inspect.getargspec(cstr).args
            problem.addConstraint(cstr, variables)
        solutions = problem.getSolutions()
        solution = solutions[random.randint(0,len(solutions)-1)]
        for var in self._randVariables:
            setattr(self, var, solution[var]) 
    
