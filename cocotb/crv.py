
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
    
