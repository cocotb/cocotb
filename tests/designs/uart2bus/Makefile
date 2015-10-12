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

GPI_EXTRA:=
ifeq ($(TOPLEVEL_LANG),verilog)
    VERILOG_SOURCES += $(SRC_BASE)/top/verilog_toplevel.v
    TOPLEVEL = verilog_toplevel
    GPI_IMPL=vpi

ifeq ($(SIM),aldec)
    GPI_EXTRA=vhpi
endif
ifeq ($(SIM),modelsim)
    GPI_EXTRA=fli
endif
ifeq ($(SIM),ius)
    GPI_EXTRA=vhpi
endif

else
$(error "Only verilog toplevel supported at the moment")
endif

ifneq ($(GPI_EXTRA),)
	include $(COCOTB)/makefiles/Makefile.inc
	include $(COCOTB)/makefiles/Makefile.sim
else
all:
	@echo "Skipping test as VHDL not supported on simulator=$(SIM)"
clean::
endif

