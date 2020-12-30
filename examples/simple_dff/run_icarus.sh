#!/bin/sh
export LIBPYTHON_LOC=$(cocotb-config --libpython)
rm -rf sim_build/
mkdir sim_build/
iverilog -o sim_build/sim.vvp -s dff -g2012 dff.sv
MODULE=test_dff vvp -M $(cocotb-config --prefix)/cocotb/libs -m libcocotbvpi_icarus sim_build/sim.vvp
