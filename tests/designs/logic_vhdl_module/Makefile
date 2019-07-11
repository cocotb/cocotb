TOPLEVEL_LANG ?= vhdl

ifneq ($(TOPLEVEL_LANG),vhdl)

all:
	@echo "Skipping test due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being vhdl"
clean::

else

TOPLEVEL := logic_testbench

ifeq ($(OS),Msys)
WPWD=$(shell sh -c 'pwd -W')
else
WPWD=$(shell pwd)
endif

COCOTB?=$(WPWD)/../../..

VHDL_SOURCES = $(COCOTB)/tests/designs/logic_vhdl_module/logic_testbench.vhd

include $(COCOTB)/makefiles/Makefile.inc
include $(COCOTB)/makefiles/Makefile.sim

endif
