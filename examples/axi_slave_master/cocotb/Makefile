SIM=ghdl
VHDL_SOURCES =$(PWD)/../hdl/axi_slave_master.vhd\
				$(PWD)/../hdl/axi_slave_master_M00_AXI.vhd\
				$(PWD)/../hdl/axi_slave_master_S00_AXI.vhd
TOPLEVEL=axi_slave_master
MODULE=test_$(TOPLEVEL)
SIM_ARGS=--wave=$(TOPLEVEL).ghw
include $(COCOTB)/makefiles/Makefile.inc
include $(COCOTB)/makefiles/Makefile.sim
