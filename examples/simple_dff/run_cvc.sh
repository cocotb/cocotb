#!/bin/sh
export LIBPYTHON_LOC=$(cocotb-config --libpython)
rm -rf sim_build/
mkdir sim_build/
MODULE=test_dff cvc64 +interp +acc+2 -o sim_build/sim.vvp +loadvpi=$(cocotb-config --prefix)/cocotb/libs/libcocotbvpi_modelsim:vlog_startup_routines_bootstrap dff.sv
