#!/usr/bin/env python

''' Copyright (c) 2013 Potential Ventures Ltd
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

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
    Determines how to execute the cocotb world
"""

import os, sys, inspect
from subprocess import call

class SimType():
    def __init__(self, name=None):
        self._name = name;

    def execute(self):
        print("Running cocotb against %s simulator" % self._name)

class SimIcarus(SimType):
    def __init__(self, name=None):
        SimType.__init__(self, "Icarus")
        self._base_cmd = ' vvp -m cocotb'

    def execute(self, py_path, lib_path, module, function, finput):
        SimType.execute(self)
        cmd = 'PYTHONPATH=' + py_path
        cmd = cmd + ' LD_LIBRARY_PATH=' + lib_path
        cmd = cmd + ' MODULE=' + module
        cmd = cmd + ' FUNCTION=' + function
        cmd = cmd + self._base_cmd
        cmd = cmd + ' -M ' + lib_path
        cmd = cmd + ' ' + finput
        print(cmd)
        call(cmd, shell=True)

class SimSfsim(SimType):
    def __init__(self, name=None):
    SimType.__init__(self, "SolarFlare Model")

    def execute(self, py_path, lib_path, module, function, finput):
        SimType.execute(self)
        cmd = 'PYTHONPATH=' + py_path
        cmd = cmd + ' LD_LIBRARY_PATH=' + lib_path
        cmd = cmd + ' MODULE=' + module
        cmd = cmd + ' FUNCTION=' + function
        cmd = cmd + ' ' + finput
        cmd = cmd + ' -l ' + lib_path + '/libcocotb.so'
        print(cmd)
        call(cmd, shell=True)

def main():

    """ Start the desired simulator with cocotb embedded within.

Options:
  -h, --help		Show this message and exit
  -f, --function	Function within Module to execute
  -m, --module		Module to load with test case
  -s, --simtype		The Simulator to use for execution
  -i, --input		Input file, type depends on simtype
"""

    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-m", "--module", dest="module_str",
                      help="Module to load with test case")
    parser.add_option("-f", "--function", dest="function_str",
                      help="Function within Module to execute")
    parser.add_option("-s", "--simtype", dest="sim_str",
                      help="The Simulator to use for execution")
    parser.add_option("-i", "--input", dest="input_str",
                      help="Input file, type depends on simtype")

    (options, args) = parser.parse_args()

    if not options.module_str:
        print main.__doc__
        sys.exit(1)

    if not options.function_str:
        print main.__doc__
        sys.exit(1)

    if not options.sim_str:
        print main.__doc__
        sys.exit(1)

    if not options.input_str:
	print main.__doc__
        sys.exit(1)

    class_name_l = options.sim_str.lower()
    class_name = 'Sim' + class_name_l[0].upper() + class_name_l[1:]

    try:
        ctype = globals()[class_name]
    except KeyError as e:
        print ("Specified name is not valid (%s)" % class_name)
        sys.exit(1)

    # Get the library paths from the current location of the cocotbenv binary
    # and the arch that it is running on
    exec_path = inspect.getfile(inspect.currentframe())
    base_path = exec_path.split('/bin', 1)[0]
    lib_path = base_path + '/build/libs/i686'
    py_path = base_path
    py_path = py_path + ':' + lib_path
    py_path = py_path + ':' + os.getcwd()

    # Add the module and function as command line options that are passed
    # as env vars to the underlying code

    sim_world = ctype()
    sim_world.execute(py_path,
                      lib_path,
                      options.module_str,
                      options.function_str,
                      options.input_str)

if __name__ == "__main__":
    main()
