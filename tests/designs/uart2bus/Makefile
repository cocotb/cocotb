SRC_BASE = $(COCOTB)/tests/designs/uart2bus

TOPLEVEL_LANG ?= verilog

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

ifeq ($(TOPLEVEL_LANG),verilog)
    VERILOG_SOURCES += $(SRC_BASE)/top/verilog_toplevel.v
    TOPLEVEL = verilog_toplevel
else
$(error "Only verilog toplevel supported at the moment")
endif

include $(COCOTB)/makefiles/Makefile.inc
include $(COCOTB)/makefiles/Makefile.sim
