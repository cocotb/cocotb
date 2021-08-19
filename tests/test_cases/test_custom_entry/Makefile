export PYTHONPATH := .
export PYGPI_ENTRY_POINT := custom_entry:entry_func

.PHONY: override_for_this_test
override_for_this_test:
	-$(MAKE) all
	python -c 'assert open("results.log").readlines() == open("expected_results.log").readlines()'

include ../../designs/sample_module/Makefile
