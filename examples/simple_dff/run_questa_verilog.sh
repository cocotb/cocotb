#!/bin/sh
export LIBPYTHON_LOC=$(cocotb-config --libpython)
rm -rf sim_build/
mkdir sim_build/
vlib sim_build/work
vmap work sim_build/work
vlog -work work +acc dff.sv
MODULE=test_dff vsim -64 -batch -pli "$(cocotb-config --prefix)/cocotb/libs/libcocotbvpi_modelsim.so" sim_build/work.dff -do "run -all; exit"
