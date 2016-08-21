
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
        self._distributions = {}
    
    def addRand(self, var, domain):
        self._randVariables[var] = domain #add variable to the map
        self._problem.addVariable(var, domain)
        self._distributions[var] = lambda _: 1 #uniform distribution
    
    def addConstraint(self, constraint):
        variables = inspect.getargspec(constraint).args
        self._problem.addConstraint(constraint, variables)
        
    def addDistribution(self, var, distribution):
        self._distributions[var] = distribution
        
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
        solution = self.resolve(problem)
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
        solution = self.resolve(problem)
        for var in self._randVariables:
            setattr(self, var, solution[var]) 
            
    def resolve(self, problem):
        solutions = problem.getSolutions()
        solution_weights = []
        for sol in solutions: #take single solution
            weight = 1.0
            for var in self._randVariables:
                weight = weight*self._distributions[var](sol[var]) #calculate weight of total solution
            solution_weights.append(weight)
        #numpy should be used instead...
        #solution = numpy.random.choice(solutions,size=1,p=solution_weights) #pick weighted random
        #if numpy not available
        min_weight = min(weight for weight in solution_weights if weight > 0)
        solution_weights = map (lambda x: int(x*(1/min_weight)), solution_weights) #convert weights to int
        weighted_solutions = []
        for x in range(len(solutions)):
            weighted_solutions = weighted_solutions + \
              [solutions[x] for _ in range(solution_weights[x])] #multiply each solution in list accordingly
        return random.choice(weighted_solutions)
        
    
