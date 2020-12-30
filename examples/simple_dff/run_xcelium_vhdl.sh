#!/bin/sh
export LIBPYTHON_LOC=$(cocotb-config --libpython)
rm -rf sim_build/
mkdir sim_build/
GPI_EXTRA=cocotbvhpi_ius:cocotbvhpi_entry_point MODULE=test_dff xrun -clean -64 -access +rwc -loadvpi $(cocotb-config --prefix)/cocotb/libs/libcocotbvpi_ius:vlog_startup_routines_bootstrap -top dff dff.vhdl
