
.PHONY: custom_entry_test
custom_entry_test:
	$(MAKE) all COCOTB_ENTRY=example_entry:entry_object.entry_func
	# ensure custom entry point is loaded and run as expected
	python check_results.py

include ../../designs/sample_module/Makefile
