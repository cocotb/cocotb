#!/bin/sh
export LIBPYTHON_LOC=$(cocotb-config --libpython)
rm -rf sim_build/
mkdir sim_build/
ghdl -i --workdir=sim_build --work=work dff.vhdl
ghdl -m --workdir=sim_build -Psim_build --work=work dff
MODULE=test_dff ghdl -r --workdir=sim_build -Psim_build --work=work dff --vpi=$(cocotb-config --prefix)/cocotb/libs/libcocotbvpi_ghdl.so
