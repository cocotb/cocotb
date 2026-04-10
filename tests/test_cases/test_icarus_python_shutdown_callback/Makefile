# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

# Icarus can invoke VPI callbacks after cocotb has called Py_Finalize(), which
# used to segfault in handle_gpi_callback() -> PyGILState_Ensure().
# Other simulators use different shutdown ordering; this regression is Icarus-only.

TOPLEVEL_LANG ?= verilog

ifneq ($(shell echo $(SIM) | tr A-Z a-z),icarus)

all:
	@echo "Skipping test_icarus_python_shutdown_callback (SIM=$(SIM) is not Icarus)"

clean::

else

# Original repro (cocotbext-jtag test003, CI) used no waveform dump; Icarus 13
# + vvp -none is where the post-Py_Finalize VPI callback showed up most clearly.
WAVES := 0
export WAVES

include ../../designs/sample_module/Makefile

COCOTB_TEST_MODULES := test_icarus_python_shutdown_callback

endif
