SIM ?= ghdl
TOPLEVEL_LANG ?= vhdl
VHDL_SOURCES_blib := b.vhdl
VHDL_SOURCES := a.vhdl
TOPLEVEL := a
MODULE := test_ab

ifneq ($(filter $(SIM),xcelium),)
    COMPILE_ARGS += -v93
endif

ifneq ($(shell echo $(TOPLEVEL_LANG) | tr A-Z a-z),vhdl)
all:
	@echo "Skipping test since only VHDL is supported"
clean::
else ifeq ($(filter ghdl questa modelsim xcelium,$(shell echo $(SIM) | tr A-Z a-z)),)
all:
	@echo "Skipping test since only GHDL, Questa/ModelSim and Xcelium are supported"
clean::
else
include $(shell cocotb-config --makefiles)/Makefile.sim
endif
