#!/bin/sh
export LIBPYTHON_LOC=$(cocotb-config --libpython)
rm -rf sim_build/
mkdir sim_build/
vlib sim_build/work
vmap work sim_build/work
vcom -work work "+acc" dff.vhdl
MODULE=test_dff vsim -64 -batch -foreign "cocotb_init $(cocotb-config --prefix)/cocotb/libs/libcocotbfli_modelsim.so" sim_build/work.dff -do "run -all; exit"
