###############################################################################
# Copyright (c) 2013 Potential Ventures Ltd
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
###############################################################################

include makefiles/Makefile.inc
include version

export BUILD_DIR=$(shell pwd)/build

INSTALL_DIR?=/usr/local
FULL_INSTALL_DIR=$(INSTALL_DIR)/cocotb-$(VERSION)

LIBS:= lib/simulator lib/embed lib/vpi_shim lib/gpi

.PHONY: $(LIBS)

libs_native: $(LIBS)

libs_64_32:
	ARCH=i686 make

inst_64_32:
	ARCH=i686 make lib_install

ifeq ($(ARCH),x86_64)
libs: libs_native libs_64_32
install_lib: lib_install inst_64_32
else
libs: libs_native
install_lib: lib_install
endif

$(LIBS): dirs
	$(MAKE) -C $@

lib/vpi_shim: lib/gpi lib/embed
lib/simulator: lib/vpi_shim

dirs:
	@mkdir -p $(LIB_DIR)

clean:
	-@rm -rf $(BUILD_DIR)
	-@find . -name "obj" | xargs rm -rf
	-@find . -name "*.pyc" | xargs rm -rf
	-@find . -name "results.xml" | xargs rm -rf

test: $(LIBS)
	$(MAKE) -C examples

pycode:
	@cp -R $(SIM_ROOT)/cocotb $(FULL_INSTALL_DIR)/

lib_install:
	@mkdir -p $(FULL_INSTALL_DIR)/lib/$(ARCH)
	@mkdir -p $(FULL_INSTALL_DIR)/bin
	@cp -R $(LIB_DIR)/* $(FULL_INSTALL_DIR)/lib/$(ARCH)

common_install:
	@cp -R bin/cocotbenv.py $(FULL_INSTALL_DIR)/bin/
	@cp -R bin/create_project.py $(FULL_INSTALL_DIR)/bin/
	@cp -R makefiles $(FULL_INSTALL_DIR)/
	@rm -rf $(FULL_INSTALL_DIR)/makefiles/Makefile.inc

create_files:
	bin/create_files.py $(FULL_INSTALL_DIR)

install: install_lib common_install pycode create_files
	@echo -e "\nInstalled to $(FULL_INSTALL_DIR)"
	@echo -e "To uninstall run $(FULL_INSTALL_DIR)/bin/cocotb_uninstall\n"

help:
	@echo -e "\nCoCoTB make help\n\nall\t- Build libaries for native"
	@echo -e "libs\t- Build libs for possible ARCHs"
	@echo -e "install\t- Build and install libaries to FULL_INSTALL_DIR (default=$(FULL_INSTALL_DIR))"
	@echo -e "clean\t- Clean the build dir\n\n"
