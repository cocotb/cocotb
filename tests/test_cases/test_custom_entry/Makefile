export PYTHONPATH := .
export PYGPI_USERS := custom_entry:entry_func

SKIP := 0
ifeq ($(SIM),riviera)
  # Determine the version of Riviera-PRO being used.
  # Assume "python3" to be available, the exact version does not matter much
  # in this context.
  RIVIERA_VERSION_INT := $(shell vsimsa -version | python3 -c 'import re,sys; m=re.match(r".+version (\d+)\.(\d+).+", sys.stdin.read()); print(f"{int(m[1])*100+int(m[2])}")')

  ifeq ($(shell test $(RIVIERA_VERSION_INT) -lt 202404; echo $$?),0)
    $(info Skipping test for Riviera-PRO versions < 2024.04 due to a hang (#3467))
    SKIP := 1
  endif
endif

ifeq ($(SKIP),1)
all:
	@echo "Skipping test"
clean::

else
.PHONY: override_for_this_test
override_for_this_test:
	-$(MAKE) all
	python -c 'import filecmp; assert filecmp.cmp("results.log", "expected_results.log")'

include ../../designs/sample_module/Makefile

endif
