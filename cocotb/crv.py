
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
import itertools

class Randomized(object):

    def __init__(self):
        #all random variables, map NAME -> DOMAIN
        self._randVariables = {} 
        #all simple constraints: functions of single random variable and optional non-random variables
        #map VARIABLE NAME -> FUNCTION
        self._simpleConstraints = {} 
        #all implicit constraints: functions that requires to be resolved by a Solver
        #map TUPLE OF VARIABLE NAMES -> FUNCTION
        self._implConstraints = {} 
        #all implicit distributions: functions that involve implicit random variables and single 
        #unconstrained variable
        #map TUPLE OF VARIABLE NAMES -> FUNCTION
        self._implDistributions = {} 
        #all simple distributions: functions of unconstrained random variables and non-random variables
        #map VARIABLE NAME -> FUNCTION
        self._simpleDistributions = {} 
    
    def addRand(self, var, domain=None):
        assert (not (self._simpleConstraints or self._implConstraints or self._implDistributions or
             self._simpleDistributions)), "All random variable must be defined before adding a costraint"
             
        if not domain:
            domain = range(65535) #16 bit unsigned int
                 
        self._randVariables[var] = domain #add a variable to the map

    def addConstraint(self, cstr):
        
        if isinstance(cstr, constraint.Constraint):
            #could be a Constraint object...
            pass
        else:
            variables = inspect.getargspec(cstr).args
            assert (variables == sorted(variables)), "Variables of constraint function must be in alphabetic order"
            
            #determine the function type... rather unpythonic but necessary for distinction between 
            #a constraint and a distribution
            callargs = []
            rand_variables = []
            for var in variables:
                if var in self._randVariables:
                    rand_variables.append(var)
                    callargs.append(random.choice(self._randVariables[var]))
                else:
                    callargs.append(getattr(self, var))
                
            ret = cstr(*callargs)
            
            def _addToMap(_key, _map):
                overwriting = None
                if _key in _map:
                    overwriting = _map[_key]
                _map[_key] = cstr
                return overwriting
            
            if type(ret) == bool:
                #this is a constraint  
                if (len(rand_variables) == 1):
                    overwriting = _addToMap(rand_variables[0], self._simpleConstraints)
                else:
                    overwriting = _addToMap(tuple(rand_variables), self._implConstraints)
            else:
                #this is a distribution
                if (len(rand_variables) == 1):
                    overwriting = _addToMap(rand_variables[0], self._simpleDistributions)
                else:
                    overwriting = _addToMap(tuple(rand_variables), self._implDistributions)

            #print "adding " + inspect.getsource(cstr)
            return overwriting
                    
    def delConstraint(self, cstr):
        
        if isinstance(cstr, constraint.Constraint):
            #could be a Constraint object...
            pass
        else:
            variables = inspect.getargspec(cstr).args
            
            rand_variables = [var for var in variables if var in self._randVariables]
            
            if (len(rand_variables) == 1):
                if rand_variables[0] in self._simpleConstraints:
                    del self._simpleConstraints[rand_variables[0]]
                elif rand_variables[0] in self._simpleDistributions:
                    del self._simpleDistributions[rand_variables[0]]
                else:
                    assert(0), "Could not delete a constraint!"
            else:
                if tuple(rand_variables) in self._implConstraints:
                    del self._implConstraints[tuple(rand_variables)]
                elif tuple(rand_variables) in self._simpleDistributions:
                    del self._implDistributions[tuple(rand_variables)]
                else:
                    assert(0), "Could not delete a constraint!"
            
            #print "removing " + inspect.getsource(cstr) 
        
    def pre_randomize(self):
        pass
    
    def post_randomize(self):
        pass
        
    def randomize(self, *constraints):
        """
        Randomizes a final class using only predefined constraints.
        """        
        self.pre_randomize()
        solution = self._resolve()
        self.post_randomize()
        
        self._update_variables(solution)
        
    def randomize_with(self, *constraints):
        """
        Randomizes a final class using additional constraints given in an argument.
        """                   
        
        overwritten_constrains = []
        
        #add new constraints
        for cstr in constraints:
            overwritten = self.addConstraint(cstr)
            if overwritten:
                overwritten_constrains.append(overwritten)
        
        self.pre_randomize()
        solution = self._resolve()
        self.post_randomize()
        
        self._update_variables(solution)
        
        #remove new constraints
        for cstr in constraints:
            self.delConstraint(cstr)
        
        #add back overwritten constraints
        for cstr in overwritten_constrains:
            self.addConstraint(cstr)

            
    def _resolve(self):
                
        #step 1: determine search space by applying simple constraints to the random variables
        
        randVariables = dict(self._randVariables) #we need a copy, as we will be updating domains
        
        for rvar in randVariables:
            domain = randVariables[rvar]
            new_domain = []
            if rvar in self._simpleConstraints:
                f_cstr = self._simpleConstraints[rvar] #a simple constratint function to be applied
                #check if we have non-random vars in cstr...
                f_c_args = inspect.getargspec(f_cstr).args #arguments of the constraint function
                for ii in domain:
                    f_cstr_callvals = []
                    for f_c_arg in f_c_args:
                        if (f_c_arg == rvar):
                            f_cstr_callvals.append(ii)
                        else:
                            f_cstr_callvals.append(getattr(self, f_c_arg))
                    #call simple constraint for each domain element        
                    if f_cstr(*f_cstr_callvals):
                        new_domain.append(ii)
                randVariables[rvar] = new_domain #update the domain with the constrained one
            
        #step 2: resolve implicit constraints using external solver
                
        #we use external hard constraint solver here - file constraint.py
        problem = constraint.Problem()
        
        constrainedVars = [] #all random variables for the solver
        
        for rvars in self._implConstraints:
            #add all random variables
            for rvar in rvars:
                if not rvar in constrainedVars:
                    problem.addVariable(rvar, randVariables[rvar])
                    constrainedVars.append(rvar)
            #add constraint
            problem.addConstraint(self._implConstraints[rvars],rvars)
            
        #solve problem
        solutions = problem.getSolutions()
        
        #step 3: calculate implicit ditributions for all random variables except simple distributions
        
        distrVars = [] #all variables that have defined distribution functions
        dsolutions = [] #soltuions with applied distribution weights - list of maps VARIABLE -> VALUE
        
        for dvars in self._implDistributions:
            #add all variables that have defined distribution functions
            for dvar in dvars:
                if dvar not in distrVars:
                    distrVars.append(dvar)
                    
        #all variables that have defined distributions but uncostrained
        ducVars = [var for var in distrVars if var not in constrainedVars]
                     
        #list of domains of random uncostrained variables
        ducDomains = [randVariables[var] for var in ducVars]
        
        #Cartesian product of above
        ducSolutions = list(itertools.product(*ducDomains))
        
        #merge solutions: constrained ones and all possible distribtion values
        for sol in solutions: 
            for ducsol in ducSolutions:
                dsol = dict(sol) 
                jj = 0
                for var in ducVars:
                    dsol[var] = ducsol[jj]
                    jj += 1
                dsolutions.append(dsol)
                
        dsolution_weights = []
        dsolutions_reduced = []
        
        for dsol in dsolutions: #take each solution
            weight = 1.0
            #for all defined implicit distributions
            for dstr in self._implDistributions:
                f_idstr = self._implDistributions[dstr]
                f_id_args = inspect.getargspec(f_idstr).args 
                #all variables in solution we need to calculate weight
                f_id_callvals = []
                for f_id_arg in f_id_args: #for each variable name
                    if f_id_arg in dsol: #if exists in solution
                        f_id_callvals.append(dsol[f_id_arg]) 
                    else: #get as non-random variable
                        f_id_callvals.append(getattr(self, f_id_arg)) 
                #update weight of the solution - call dstribution function
                weight = weight*f_idstr(*f_id_callvals) 
            #do the same for simple distributions
            for dstr in self._simpleDistributions:
                #but only if variable is already in the solution
                #if it is not, it will be calculated in step 4
                if dstr in sol: 
                    f_sdstr = self._simpleDistributions[dstr]
                    f_sd_args = inspect.getargspec(f_sdstr).args 
                    #all variables in solution we need to calculate weight
                    f_sd_callvals = []
                    for f_sd_arg in f_sd_args: #for each variable name
                        if f_sd_arg in dsol: #if exists in solution
                            f_sd_callvals.append(dsol[f_sd_arg]) 
                        else: #get as non-random variable
                            f_sd_callvals.append(getattr(self, f_sd_arg)) 
                    #update weight of the solution - call dstribution function
                    weight = weight*f_sdstr(*f_sd_callvals) 
            if (weight > 0.0):
                dsolution_weights.append(weight)
                dsolutions_reduced.append(dsol) #remove solutions with weight = 0
                        
        solution_choice = self._weighted_choice(dsolutions_reduced, dsolution_weights)
        solution = solution_choice if solution_choice is not None else {}
        
        #step 4: calculate simple ditributions for remaining random variables
        for dvar in randVariables:
            if not dvar in solution: #must be already unresolved variable
                domain = randVariables[dvar]
                weights = []
                if dvar in self._simpleDistributions:
                    f_dstr = self._simpleDistributions[dvar] #a simple distribution to be applied
                    #check if we have non-random vars in dstr...
                    f_d_args = inspect.getargspec(f_dstr).args 
                    f_d_callvals = [] #list of lists of values for function call
                    for i in domain:
                        f_d_callval = []
                        for f_d_arg in f_d_args:
                            if (f_d_arg == dvar):
                                f_d_callval.append(i)
                            else:
                                f_d_callval.append(getattr(self, f_d_arg))
                        f_d_callvals.append(f_d_callval)
                    #call distribution function for each domain element to get the weight
                    weights = [f_dstr(*f_d_callvals_i) for f_d_callvals_i in f_d_callvals] 
                    new_solution = self._weighted_choice(domain, weights)
                    if new_solution is not None:
                        solution[dvar] = new_solution #append chosen value to the solution 
                else:
                    #random variable has no defined distribution function - call simple random.choice
                    solution[dvar] = random.choice(domain) 
        
        return solution
        
    def _weighted_choice(self, solutions, weights):
        try:
            import numpy
            return numpy.random.choice(solutions,size=1,p=weights) #pick weighted random
        except:
            #if numpy not available
            non_zero_weights = [x for x in weights if x > 0]
            
            if not non_zero_weights:
                return None
            
            min_weight = min(non_zero_weights)
            
            weighted_solutions = []
            
            for x in range(len(solutions)):
                #insert each solution to the list multiple times 
                weighted_solutions.extend([solutions[x] for _ in range(int(weights[x]*(1.0/min_weight)))])
              
            return random.choice(weighted_solutions)
        
    def _update_variables(self, solution):
        #update class members
        for var in self._randVariables:
            if var in solution:
                setattr(self, var, solution[var])             
        
    
