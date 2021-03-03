# detecting an expected failure has to happen here, as the python code is invalid
.PHONY: override_for_this_test
override_for_this_test:
	if $(MAKE) all; then echo "Expected this to fail"; false; else echo "Failed as expected"; fi

include ../../designs/sample_module/Makefile

# This module exists, but...
MODULE := x_tests
# ...this test does not exist, so an error should be raised
TESTCASE := y_test
