TOPLEVEL_LANG ?= verilog

ifneq ($(TOPLEVEL_LANG),verilog)

all:
	@echo "Skipping test due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being verilog"
clean::

else

PWD=$(shell pwd)

COCOTB?=$(PWD)/../../..

SRC_BASE = $(COCOTB)/tests/designs/uart2bus

VHDL_SOURCES =      $(SRC_BASE)/vhdl/uart2BusTop_pkg.vhd \
                    $(SRC_BASE)/vhdl/baudGen.vhd \
                    $(SRC_BASE)/vhdl/uartParser.vhd \
                    $(SRC_BASE)/vhdl/uartRx.vhd \
                    $(SRC_BASE)/vhdl/uartTx.vhd \
                    $(SRC_BASE)/vhdl/uartTop.vhd \
                    $(SRC_BASE)/vhdl/uart2BusTop.vhd

VERILOG_SOURCES =   $(SRC_BASE)/verilog/baud_gen.v \
                    $(SRC_BASE)/verilog/uart_parser.v \
                    $(SRC_BASE)/verilog/uart_rx.v \
                    $(SRC_BASE)/verilog/uart_tx.v \
                    $(SRC_BASE)/verilog/uart_top.v \
                    $(SRC_BASE)/verilog/uart2bus_top.v

VERILOG_SOURCES += $(SRC_BASE)/top/verilog_toplevel.sv
TOPLEVEL = verilog_toplevel

ifeq ($(SIM),$(filter $(SIM),ius xcelium))
    SIM_ARGS += -v93
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
