
TEST_DIR:=$(dir $(lastword $(MAKEFILE_LIST)))
COCOTB_DIR:=$(abspath $(TEST_DIR)/../../..)

PYTHONPATH:=$(COCOTB_DIR):$(PYTHONPATH)
export PYTHONPATH

all :
	python3 -m unittest

