export PYTHONPATH := .
export PYGPI_ENTRY_POINT := custom_entry:entry_func

.PHONY: override_for_this_test
override_for_this_test:
	-$(MAKE) all
	diff --strip-trailing-cr results.log expected_results.log &>/dev/null

include ../../designs/sample_module/Makefile
