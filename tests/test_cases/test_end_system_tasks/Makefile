# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

TOPLEVEL_LANG ?= verilog
TOPLEVEL := test_end_system_tasks
MODULE := test_end_system_tasks
PWD=$(shell pwd)
VERILOG_SOURCES := $(PWD)/test_end_system_tasks.sv

ifneq ($(TOPLEVEL_LANG),verilog)

all::
	@echo "Skipping test due to TOPLEVEL_LANG=$(TOPLEVEL_LANG) not being verilog"

clean::

else

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
