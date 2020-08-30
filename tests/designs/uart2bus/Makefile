TOPLEVEL_LANG ?= verilog

PWD=$(shell pwd)

COCOTB?=$(PWD)/../../..

SRC_BASE = $(COCOTB)/tests/designs/uart2bus

VHDL_SOURCES += $(SRC_BASE)/vhdl/uart2BusTop_pkg.vhd
VHDL_SOURCES += $(SRC_BASE)/vhdl/baudGen.vhd
VHDL_SOURCES += $(SRC_BASE)/vhdl/uartParser.vhd
VHDL_SOURCES += $(SRC_BASE)/vhdl/uartRx.vhd
VHDL_SOURCES += $(SRC_BASE)/vhdl/uartTx.vhd
VHDL_SOURCES += $(SRC_BASE)/vhdl/uartTop.vhd
VHDL_SOURCES += $(SRC_BASE)/vhdl/uart2BusTop.vhd
VHDL_SOURCES += $(SRC_BASE)/top/vhdl_toplevel.vhdl

VERILOG_SOURCES += $(SRC_BASE)/verilog/baud_gen.v
VERILOG_SOURCES += $(SRC_BASE)/verilog/uart_parser.v
VERILOG_SOURCES += $(SRC_BASE)/verilog/uart_rx.v
VERILOG_SOURCES += $(SRC_BASE)/verilog/uart_tx.v
VERILOG_SOURCES += $(SRC_BASE)/verilog/uart_top.v
VERILOG_SOURCES += $(SRC_BASE)/verilog/uart2bus_top.v
VERILOG_SOURCES += $(SRC_BASE)/top/verilog_toplevel.sv

ifneq ($(TOPLEVEL_LANG),verilog)
    TOPLEVEL = vhdl_toplevel
else
    TOPLEVEL = verilog_toplevel
endif

ifeq ($(SIM),$(filter $(SIM),ius xcelium))
    SIM_ARGS += -v93
    # needed for the two different possible toplevels:
    SIM_ARGS += -smartorder
endif

include $(shell cocotb-config --makefiles)/Makefile.sim
