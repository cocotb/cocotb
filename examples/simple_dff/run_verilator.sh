#!/bin/sh
export LIBPYTHON_LOC=$(cocotb-config --libpython)
rm -rf sim_build/
mkdir sim_build/
verilator -cc --exe -Mdir sim_build --top-module dff --vpi --public-flat-rw --prefix Vtop -o dff -LDFLAGS "-Wl,-rpath,$(cocotb-config --prefix)/cocotb/libs -L$(cocotb-config --prefix)/cocotb/libs -lcocotbvpi_verilator -lgpi -lcocotb -lgpilog -lcocotbutils" dff.sv $(cocotb-config --share)/lib/verilator/verilator.cpp
CPPFLAGS="-std=c++11" make -C sim_build -f Vtop.mk
MODULE=test_dff sim_build/dff
