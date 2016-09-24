
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
Constrained-random verification features.

Classes:
Randomized - base class for objects intended to contain random variables
"""

import random
import constraint
import inspect
import itertools

class Randomized(object):
    """
    Base class for randomized types. Final class should contain defined random 
    variables using addRand() method. Constraints may be added/deleted using 
    add/delConstraint() methods. 
    Constraint is an arbitrary function and may either return a true/false value
    (hard constraints) or a numeric value, which may be interpreted as soft 
    constraints or distribution functions. Constraint function arguments must 
    match final class attributes (random or not). Constraints may have multiple 
    random arguments which corresponds to multi-dimensional distributions.
    Function randomize() performs a randomization for all random variables 
    meeting all defined  constraints. 
    Function randomize_with() performs a randomization using additional 
    constraint functions given in an argument.
    Functions pre/post_randomize() are called before/after randomize and should 
    be overloaded in a final class if necessary. 
    If a hard constraint cannot be resolved, an exception is thrown. If a soft
    constraint cannot be resolved (all acceptable solutions have 0 probability)
    a variable value is not being randomized. 

    Example:
    class FinalRandomized(Randomized)
      def __init__(self, x):
        Randomized.__init__(self)
        self.x = x
        self.y = 0
        self.z = 0
        #define y as a random variable taking values from 0 to 9
        addRand(y, list(range(10)))
        #define z as a random variable taking values from 0 to 4
        addRand(z, list(range(5)))  
        addConstraint(lambda x, y: x !=y ) #hard constraint
        addConstraint(lambda y, z: y + z ) #multi-dimensional distribution

    object = FinalRandomized(5)
    object.randomize_with(lambda z : z > 3) #additional constraint to be applied

    As generating constrained random objects may involve a lot of computations, 
    it is recommended to limit random variables domains and use 
    pre/post_randomize() methods where possible. 
    """
    def __init__(self):
        # all random variables, map NAME -> DOMAIN
        self._randVariables = {}
        
        # all simple constraints: functions of single random variable and
        # optional non-random variables
        # map VARIABLE NAME -> FUNCTION
        self._simpleConstraints = {}
        
        # all implicit constraints: functions that requires to be resolved by a
        # Solver
        # map TUPLE OF VARIABLE NAMES -> FUNCTION
        self._implConstraints = {}
        
        # all implicit distributions: functions that involve implicit random
        # variables and single unconstrained variable
        # map TUPLE OF VARIABLE NAMES -> FUNCTION
        self._implDistributions = {}
        
        # all simple distributions: functions of unconstrained random variables
        # and non-random variables
        # map VARIABLE NAME -> FUNCTION
        self._simpleDistributions = {}
        
        # list of lists containing random variables solving order
        self._solveOrder = []

    def addRand(self, var, domain=None):
        """
        Adds a random variable to the solver. All random variables must be 
        defined before adding any constraint. Therefore it is highly 
        recommended to do this in an __init__ method. 
        Syntax:
        addRand(var, domain)
        Where:
        var - a variable name (str) corresponding to the class member variable
        domain - a list of all allowed values of the variable var

        Examples:
        addRand("data", list(range(1024)))
        addRand("delay", ["small", "medium", "high"])
        """
        assert (not (self._simpleConstraints or
                     self._implConstraints or
                     self._implDistributions or
                     self._simpleDistributions)
                ), \
            "All random variable must be defined before adding a constraint"

        if not domain:
            domain = range(65535)  # 16 bit unsigned int

        self._randVariables[var] = domain  # add a variable to the map

    def addConstraint(self, cstr):
        """
        Adds a constraint function to the solver. A constraint may return a 
        true/false or a numeric value. Constraint function arguments must be 
        valid class member names (random or not). Arguments must be listed in 
        alphabetical order. Due to calculation complexity, it is recommended to 
        create as few constraints as possible and implement pre/post 
        randomization methods or use solveOrder() function.
        Each constraint is associated with its arguments being random variables, 
        which means for each random variable combination only one constraint of 
        the true/false type and one numeric may be defined. The latter will 
        overwrite the existing one. For example, when class has two random 
        variables (x,y), 6 constraint functions may be defined: boolean and 
        numeric constraints of x, y and a pair (x,y).  
        Syntax:
        (ovewritting = )addConstraint(cstr)
        Where:
        cstr - a constraint function
        overwritting - returns an overwritten constraint or None if no overwrite
                       happened (optional)

        Examples:
        def highdelay_cstr(delay):
          delay == "high"
        addConstraint(highdelay_cstr) #hard constraint
        addConstraint(lambda data : data < 128) #hard constraint
        #distribution (highest probability density at the boundaries):
        addConstraint(lambda data : abs(64 - data)) 
        #hard constraint of multiple variables (some of them may be non-random):
        addConstraint(lambda x,y,z : x + y + z == 0) 
        #soft constraint created by applying low probability density for some 
        #solutions:
        addConstraint(
          lambda delay, size : 0.01 if (size < 5 & delay == "medium") else 1
        ) 
        #this constraint will overwrite the previously defined (data < 128)
        addConstraint(lambda data : data < 256)
        """
        
        #just add constraint considering all random variables 
        return self._addConstraint(cstr, self._randVariables)
        
    def solveOrder(self, *orderedVars):
        """
        Defines an order of the constraints resolving. May contain variable
        names or lists with variable names. Constraints are resolved in a given
        order, which means for implicit constraint and distribution functions,
        they may be treated as simple ones, as one some variables could be 
        already resolved.
        solveOrder(*orderedVars)
        Where:
        orderedVars - variables that are requested to be resolved in an specific
                      order
        Example:
        addRand (x, list(range(0,10)))
        addRand (y, list(range(0,10)))
        addRand (z, list(range(0,10)))
        addRand (w, list(range(0,10)))
        addConstraint(lambda x, y : x + y = 9)
        addConstraint(lambda z : z < 5) 
        addConstraint(lambda w : w > 5)
         
        solveOrder(["x", "z"], "y"] 
        #In first step, "z", "x" and "w" will be resolved, which means only 
        #second  and third constraint will be applied. In second step, first 
        #constraint will be resolved as it was requested to solve "y" after "x"
        #and "z". "x" will be treated as a constant in this case.      
        """
        self._solveOrder = []
        for selRVars in orderedVars:
            if type(selRVars) is not list:
                self._solveOrder.append([selRVars])
            else:
                self._solveOrder.append(selRVars)

    def delConstraint(self, cstr):
        """
        Deletes a constraint function.
        Syntax:
        delConstraint(cstr)
        Where:
        cstr - a constraint function

        Example:
        delConstraint(highdelay_cstr) 
        """
        return self._delConstraint(cstr, self._randVariables)

    def pre_randomize(self):
        """
        A function called before randomize(_with)(). To be overridden in a final 
        class if used. 
        """
        pass

    def post_randomize(self):
        """
        A function called after randomize(_with)(). To be overridden in a final 
        class if used. 
        """
        pass

    def randomize(self):
        """
        Randomizes a final class using only predefined constraints.
        """
        self._randomize()

    def randomize_with(self, *constraints):
        """
        Randomizes a final class using additional constraints given in an 
        argument. Additional constraints may override existing ones.
        """
        overwritten_constrains = []

        # add new constraints
        for cstr in constraints:
            overwritten = self.addConstraint(cstr)
            if overwritten:
                overwritten_constrains.append(overwritten)

        self._randomize()

        # remove new constraints
        for cstr in constraints:
            self.delConstraint(cstr)

        # add back overwritten constraints
        for cstr in overwritten_constrains:
            self.addConstraint(cstr)
            
    def _addConstraint(self, cstr, rvars):
        """
        Adds a constraint for a specific random variables list (which determines
        a type of a constraint - simple or implicit).
        """        
        if isinstance(cstr, constraint.Constraint):
            # could be a Constraint object...
            pass
        else:
            variables = inspect.getargspec(cstr).args
            assert (variables == sorted(variables)), \
                "Variables of a constraint function must be defined in \
                alphabetical order"

            # determine the function type... rather unpythonic but necessary for
            # distinction between a constraint and a distribution
            callargs = []
            rand_variables = []
            for var in variables:
                if var in rvars:
                    rand_variables.append(var)
                    callargs.append(random.choice(rvars[var]))
                else:
                    callargs.append(getattr(self, var))

            ret = cstr(*callargs)

            def _addToMap(_key, _map):
                overwriting = None
                if _key in _map:
                    overwriting = _map[_key]
                _map[_key] = cstr
                return overwriting

            if type(ret) is bool:
                # this is a constraint
                if (len(rand_variables) == 1):
                    overwriting = _addToMap(
                        rand_variables[0], self._simpleConstraints)
                else:
                    overwriting = _addToMap(
                        tuple(rand_variables), self._implConstraints)
            else:
                # this is a distribution
                if (len(rand_variables) == 1):
                    overwriting = _addToMap(
                        rand_variables[0], self._simpleDistributions)
                else:
                    overwriting = _addToMap(
                        tuple(rand_variables), self._implDistributions)

            return overwriting
        
    def _delConstraint(self, cstr, rvars):
        """
        Deletes a constraint for a specific random variables list (which 
        determines a type of a constraint - simple or implicit).
        """  
        if isinstance(cstr, constraint.Constraint):
            # could be a Constraint object...
            pass
        else:
            variables = inspect.getargspec(cstr).args

            rand_variables = [
                var for var in variables if var in rvars]

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
                elif tuple(rand_variables) in self._implDistributions:
                    del self._implDistributions[tuple(rand_variables)]
                else:
                    assert(0), "Could not delete a constraint!"
        
    
    def _randomize(self):
        """
        Calls _resolve and pre/post_randomize functions with respect to defined 
        variables resolving order.
        """
        self.pre_randomize()
        if not self._solveOrder:
            #call _resolve for all random variables 
            solution = self._resolve(self._randVariables)
            self._update_variables(solution)
        else:
            
            #list of random variables names
            remainingRVars = list(self._randVariables.keys())
            
            #list of resolved random variables names 
            resolvedRVars = []
            
            #list of random variables with defined solve order
            remainingOrderedRVars = [item for sublist in self._solveOrder 
                                     for item in sublist]
            
            allConstraints = [] # list of functions (all constraints and dstr)
            allConstraints.extend([self._implConstraints[_] 
                               for _ in self._implConstraints])
            allConstraints.extend([self._implDistributions[_] 
                               for _ in self._implDistributions])
            allConstraints.extend([self._simpleConstraints[_] 
                               for _ in self._simpleConstraints])
            allConstraints.extend([self._simpleDistributions[_] 
                               for _ in self._simpleDistributions])
            
            for selRVars in self._solveOrder:
                  
                #step 1: determine all variables to be solved at this stage
                actualRVars = list(selRVars) #add selected
                for rvar in actualRVars:
                    remainingOrderedRVars.remove(rvar) #remove selected
                    remainingRVars.remove(rvar) #remove selected
                
                #if implicit constraint requires a variable which is not given
                #at this stage, it will be resolved later
                for rvar in remainingRVars:
                    rvar_unused = True
                    for c_vars in self._implConstraints:
                        if rvar in c_vars:
                            rvar_unused = False
                    for d_vars in self._implDistributions:
                        if rvar in d_vars:
                            rvar_unused = False
                    if rvar_unused and not rvar in remainingOrderedRVars:
                        actualRVars.append(rvar)
                        remainingRVars.remove(rvar)
                
                # a new map of random variables
                newRandVariables = {}
                for var in self._randVariables:
                    if var in actualRVars:
                        newRandVariables[var] = self._randVariables[var]
                
                #step 2: select only valid constraints at this stage
                
                #delete all constraints and add back but considering only 
                #limited list of random vars
                actualCstr = []
                for f_cstr in allConstraints:
                    self.delConstraint(f_cstr)
                    f_cstr_args = inspect.getargspec(f_cstr).args
                    #add only constraints containing actualRVars but not
                    #remainingRVars
                    add_cstr = True
                    for var in f_cstr_args:
                        if (var in self._randVariables and 
                            not var in resolvedRVars and
                            (not var in actualRVars or var in remainingRVars)
                            ):
                            add_cstr = False
                    if add_cstr:                      
                        self._addConstraint(f_cstr, newRandVariables)
                        actualCstr.append(f_cstr)
                
                #call _resolve for all random variables 
                solution = self._resolve(newRandVariables)
                self._update_variables(solution) 
                
                resolvedRVars.extend(actualRVars)
                
                #add back everything as it was before this stage
                for f_cstr in actualCstr:
                    self._delConstraint(f_cstr, newRandVariables)
                    
                for f_cstr in allConstraints:  
                    self._addConstraint(f_cstr, self._randVariables)
                
        self.post_randomize()

    def _resolve(self, randomVariables):
        """
        Resolves constraints for given random variables.
        """
        
        # we need a copy, as we will be updating domains
        randVariables = dict(randomVariables)
        
        # step 1: determine search space by applying simple constraints to the
        # random variables

        for rvar in randVariables:
            domain = randVariables[rvar]
            new_domain = []
            if rvar in self._simpleConstraints:
                # a simple constraint function to be applied
                f_cstr = self._simpleConstraints[rvar]
                # check if we have non-random vars in cstr...
                # arguments of the constraint function
                f_c_args = inspect.getargspec(f_cstr).args
                for ii in domain:
                    f_cstr_callvals = []
                    for f_c_arg in f_c_args:
                        if (f_c_arg == rvar):
                            f_cstr_callvals.append(ii)
                        else:
                            f_cstr_callvals.append(getattr(self, f_c_arg))
                    # call simple constraint for each domain element
                    if f_cstr(*f_cstr_callvals):
                        new_domain.append(ii)
                # update the domain with the constrained one
                randVariables[rvar] = new_domain

        # step 2: resolve implicit constraints using external solver

        # we use external hard constraint solver here - file constraint.py
        problem = constraint.Problem()

        constrainedVars = []  # all random variables for the solver

        for rvars in self._implConstraints:
            # add all random variables
            for rvar in rvars:
                if not rvar in constrainedVars:
                    problem.addVariable(rvar, randVariables[rvar])
                    constrainedVars.append(rvar)
            # add constraint
            problem.addConstraint(self._implConstraints[rvars], rvars)

        # solve problem
        solutions = problem.getSolutions()
        
        if len(solutions) < len(constrainedVars):
            raise Exception("Could nor resolve implicit constraints!")

        # step 3: calculate implicit distributions for all random variables
        # except simple distributions

        # all variables that have defined distribution functions
        distrVars = []
        # solutions with applied distribution weights - list of maps VARIABLE
        # -> VALUE
        dsolutions = []

        # add all variables that have defined distribution functions
        for dvars in self._implDistributions:
            # add all variables that have defined distribution functions
            for dvar in dvars:
                if dvar not in distrVars:
                    distrVars.append(dvar)

        # all variables that have defined distributions but unconstrained
        ducVars = [var for var in distrVars if var not in constrainedVars]

        # list of domains of random unconstrained variables
        ducDomains = [randVariables[var] for var in ducVars]

        # Cartesian product of above
        ducSolutions = list(itertools.product(*ducDomains))

        # merge solutions: constrained ones and all possible distribution values
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

        for dsol in dsolutions:  # take each solution
            weight = 1.0
            # for all defined implicit distributions
            for dstr in self._implDistributions:
                f_idstr = self._implDistributions[dstr]
                f_id_args = inspect.getargspec(f_idstr).args
                # all variables in solution we need to calculate weight
                f_id_callvals = []
                for f_id_arg in f_id_args:  # for each variable name
                    if f_id_arg in dsol:  # if exists in solution
                        f_id_callvals.append(dsol[f_id_arg])
                    else:  # get as non-random variable
                        f_id_callvals.append(getattr(self, f_id_arg))
                # update weight of the solution - call distribution function
                weight = weight * f_idstr(*f_id_callvals)
            # do the same for simple distributions
            for dstr in self._simpleDistributions:
                # but only if variable is already in the solution
                # if it is not, it will be calculated in step 4
                if dstr in sol:
                    f_sdstr = self._simpleDistributions[dstr]
                    f_sd_args = inspect.getargspec(f_sdstr).args
                    # all variables in solution we need to calculate weight
                    f_sd_callvals = []
                    for f_sd_arg in f_sd_args:  # for each variable name
                        if f_sd_arg in dsol:  # if exists in solution
                            f_sd_callvals.append(dsol[f_sd_arg])
                        else:  # get as non-random variable
                            f_sd_callvals.append(getattr(self, f_sd_arg))
                    # update weight of the solution - call distribution function
                    weight = weight * f_sdstr(*f_sd_callvals)
            if (weight > 0.0):
                dsolution_weights.append(weight)
                # remove solutions with weight = 0
                dsolutions_reduced.append(dsol)

        solution_choice = self._weighted_choice(
            dsolutions_reduced, dsolution_weights)
        solution = solution_choice if solution_choice is not None else {}

        # step 4: calculate simple distributions for remaining random variables
        for dvar in randVariables:
            if not dvar in solution:  # must be already unresolved variable
                domain = randVariables[dvar]
                weights = []
                if dvar in self._simpleDistributions:
                    # a simple distribution to be applied
                    f_dstr = self._simpleDistributions[dvar]
                    # check if we have non-random vars in dstr...
                    f_d_args = inspect.getargspec(f_dstr).args
                    # list of lists of values for function call
                    f_d_callvals = []
                    for i in domain:
                        f_d_callval = []
                        for f_d_arg in f_d_args:
                            if (f_d_arg == dvar):
                                f_d_callval.append(i)
                            else:
                                f_d_callval.append(getattr(self, f_d_arg))
                        f_d_callvals.append(f_d_callval)
                    # call distribution function for each domain element to get
                    # the weight
                    weights = [f_dstr(*f_d_callvals_i)
                               for f_d_callvals_i in f_d_callvals]
                    new_solution = self._weighted_choice(domain, weights)
                    if new_solution is not None:
                        # append chosen value to the solution
                        solution[dvar] = new_solution
                else:
                    # random variable has no defined distribution function -
                    # call simple random.choice
                    solution[dvar] = random.choice(domain)

        return solution

    def _weighted_choice(self, solutions, weights):
        """
        Gets a solution from the list with defined weights.
        """
        try:
            import numpy
            # pick weighted random
            return numpy.random.choice(solutions, size=1, p=weights)
        except:
            # if numpy not available
            non_zero_weights = [x for x in weights if x > 0]

            if not non_zero_weights:
                return None

            min_weight = min(non_zero_weights)

            weighted_solutions = []

            for x in range(len(solutions)):
                # insert each solution to the list multiple times
                weighted_solutions.extend(
                    [solutions[x] for _ in range(
                        int(weights[x] * (1.0 / min_weight)))
                     ])

            return random.choice(weighted_solutions)

    def _update_variables(self, solution):
        """
        Updates members of the final class after randomization.
        """
        # update class members
        for var in self._randVariables:
            if var in solution:
                setattr(self, var, solution[var])
