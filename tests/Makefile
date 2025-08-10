# Copyright cocotb contributors
# Copyright (c) 2015 Potential Ventures Ltd
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

# Do not fail on DeprecationWarning caused by virtualenv, which might come from
# the site module.
# Do not fail on DeprecationWarning caused by attrs dropping 3.6 support
export PYTHONWARNINGS = error,ignore::DeprecationWarning:site,ignore::DeprecationWarning:attr
export COCOTB_SCHEDULER_DEBUG = 1

REGRESSIONS :=  $(shell ls test_cases/)

all: $(REGRESSIONS)

.PHONY: $(REGRESSIONS)
$(REGRESSIONS):
	@echo Running regression suite $@
	@cd test_cases/$@ && $(MAKE); ret=$$?; if [ $$ret -ne 0 ]; then echo "::error ::Failed regression suite $@"; fi; exit $$ret;

.PHONY: clean
clean:
	@for regression in $(REGRESSIONS); do \
		( cd test_cases/$$regression && make clean ); \
	done
