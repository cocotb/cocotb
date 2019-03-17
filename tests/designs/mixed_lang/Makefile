TOPLEVEL_LANG ?= verilog

ifneq ($(TOPLEVEL_LANG),verilog)

all:
	@echo "Skipping test due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being verilog"
clean::

else

ifeq ($(OS),Msys)
WPWD=$(shell sh -c 'pwd -W')
else
WPWD=$(shell pwd)
endif

COCOTB?=$(WPWD)/../../..

SRC_BASE = $(COCOTB)/tests/designs/mixed_lang

VHDL_SOURCES =      $(SRC_BASE)/counter.vhd \
                    $(SRC_BASE)/counters.vhd

VERILOG_SOURCES =   $(SRC_BASE)/mixed_lang_top.sv

TOPLEVEL = mixed_lang_top

include $(COCOTB)/makefiles/Makefile.inc
include $(COCOTB)/makefiles/Makefile.sim

endif
