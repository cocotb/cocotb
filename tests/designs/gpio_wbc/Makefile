
TOPLEVEL := gpio_top

ifeq ($(OS),Msys)
WPWD=$(shell sh -c 'pwd -W')
else
WPWD=$(shell pwd)
endif

PWD=$(shell pwd)
COCOTB=$(PWD)/../../..

VERILOG_SOURCES = $(COCOTB)/tests/designs/gpio_wbc/src/gpio_top.v

COMPILE_ARGS += -I $(COCOTB)/tests/designs/gpio_wbc/src/

include $(COCOTB)/makefiles/Makefile.inc
include $(COCOTB)/makefiles/Makefile.sim
