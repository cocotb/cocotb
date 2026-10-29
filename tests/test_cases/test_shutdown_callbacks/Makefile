# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

export PYTHONPATH := .:$(PYTHONPATH)
export PYGPI_USERS := shutdown_callbacks:entry_func

# Check after the simulator exits, since the callbacks run during shutdown.
# The custom entry point does not produce the results.xml expected by all.
.PHONY: override_for_this_test
override_for_this_test:
	@rm -f results.log
	-$(MAKE) all
	python -c 'from pathlib import Path; assert Path("results.log").read_text() == Path("expected_results.log").read_text()'

include ../../designs/sample_module/Makefile
