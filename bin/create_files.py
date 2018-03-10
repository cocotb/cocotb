#!/usr/bin/env python

''' Copyright (c) 2013 Potential Ventures Ltd
Copyright (c) 2013 SolarFlare Communications Inc
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd,
      SolarFlare Communications Inc nor the
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
script takes an input path and creates
    Makefile.inc, used to provide common information once installed
    cocotb_uninstall, uninstall script
"""
import sys
import platform
from subprocess import call


def print_make_inc(path):
    makefile = open("/tmp/Makefile.inc", "w")
    makefile.write("export ARCH:=$(shell uname -m)\n")
    makefile.write("export SIM_ROOT:=" + path + "\n")
    makefile.write("export LIB_DIR:=" + path + "/lib/$(ARCH)\n")
    makefile.close()


def print_uninstall(path):
    uninstall = open("/tmp/cocotb_uninstall", "w")
    file_contents = "#!/usr/bin/env python\n"
    file_contents = file_contents + "import sys\nfrom subprocess import call\n\n"
    file_contents = file_contents + "def remove():\n"
    file_contents = file_contents + "    print(\"Removing cocotb from " + path + "\")\n"
    file_contents = file_contents + "    call(\"rm -rf " + path + "\", shell=True)\n\n"
    file_contents = file_contents + "if __name__ == \"__main__\":\n"
    file_contents = file_contents + "   remove()\n"

    uninstall.write(file_contents)


def print_files(path):
    print_uninstall(path)

    call("install -m 544 /tmp/cocotb_uninstall " + path + "/bin/cocotb_uninstall", shell=True)
    call("rm -rf /tmp/cocotb_uninstall", shell=True)


def check_args(args):
    if len(args) is not 1:
        print("Please specify a path")
        return

    print_files(args[0])

if __name__ == "__main__":
    check_args(sys.argv[1:])
