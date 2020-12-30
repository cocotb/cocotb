#!/bin/sh
export LIBPYTHON_LOC=$(cocotb-config --libpython)
rm -rf sim_build/
mkdir sim_build/
pushd sim_build
echo "acc+=rw,wn:*" > pli.tab
vcs -full64 -debug_access+r+w+nomemcbk -debug_region+cell +vpi -P pli.tab -sverilog -load $(cocotb-config --prefix)/cocotb/libs/libcocotbvpi_vcs.so ../dff.sv -top dff
popd
MODULE=test_dff sim_build/simv
