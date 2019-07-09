TOPLEVEL_LANG ?= vhdl

ifneq ($(TOPLEVEL_LANG), vhdl)

all:
	@echo "Skipping test due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being vhdl"
clean::

else

TOPLEVEL := axi4_shim

ifeq ($(OS),Msys)
WPWD=$(shell sh -c 'pwd -W')
else
WPWD=$(shell pwd)
endif

COCOTB?=$(WPWD)/../../..

VHDL_SOURCES = $(COCOTB)/tests/designs/axi_module/AXI4.vhd

include $(COCOTB)/makefiles/Makefile.inc
include $(COCOTB)/makefiles/Makefile.sim

endif
