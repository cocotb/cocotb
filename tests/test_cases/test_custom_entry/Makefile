export PYTHONPATH := .
export PYGPI_USERS := custom_entry:entry_func

.PHONY: override_for_this_test
override_for_this_test:
	-$(MAKE) all
	python -c 'import filecmp; assert filecmp.cmp("results.log", "expected_results.log")'

include ../../designs/sample_module/Makefile
