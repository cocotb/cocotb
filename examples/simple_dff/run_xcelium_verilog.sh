#!/bin/sh
export LIBPYTHON_LOC=$(cocotb-config --libpython)
rm -rf sim_build/
mkdir sim_build/
MODULE=test_dff xrun -clean -64 -access +rwc -loadvpi $(cocotb-config --prefix)/cocotb/libs/libcocotbvpi_ius:vlog_startup_routines_bootstrap dff.sv
