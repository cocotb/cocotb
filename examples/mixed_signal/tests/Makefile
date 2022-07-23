# Override this variable to use a VHDL toplevel instead of (System)Verilog
TOPLEVEL_LANG ?= verilog

TOPLEVEL ?= tb_rescap

ifeq ($(TOPLEVEL),tb_rescap)
    MODULE ?= test_rescap,test_rescap_minimalist
else ifeq ($(TOPLEVEL),tb_regulator)
    MODULE ?= test_regulator_plot,test_regulator_trim
else
    $(error Given TOPLEVEL '$(TOPLEVEL)' not supported)
endif

ifeq ($(OS),Msys)
    WPWD=$(shell sh -c 'pwd -W')
else
    WPWD=$(shell pwd)
endif


# Files

VERILOG_SOURCES += $(WPWD)/../hdl/resistor.vams
VERILOG_SOURCES += $(WPWD)/../hdl/capacitor.vams
VERILOG_SOURCES += $(WPWD)/../hdl/regulator_block.vams

ifeq ($(SIM),$(filter $(SIM),ius xcelium))
    VERILOG_SOURCES += $(WPWD)/../hdl/analog_probe_cadence.sv
    ifeq ($(TOPLEVEL_LANG),verilog)
        VERILOG_SOURCES += $(WPWD)/../hdl/nettypes_pkg_cadence.sv
        VERILOG_SOURCES += $(WPWD)/../hdl/rescap.sv
        VERILOG_SOURCES += $(WPWD)/../hdl/regulator.sv
        VERILOG_SOURCES += $(WPWD)/../hdl/tb_rescap.sv
        VERILOG_SOURCES += $(WPWD)/../hdl/tb_regulator.sv
    else ifeq ($(TOPLEVEL_LANG),vhdl)
        $(error VHDL toplevel not yet implemented)
        VHDL_SOURCES += $(WPWD)/../hdl/rescap.vhdl
        VHDL_SOURCES += $(WPWD)/../hdl/regulator.vhdl
    else
        $(error A valid value (verilog or vhdl) was not provided for TOPLEVEL_LANG=$(TOPLEVEL_LANG))
    endif
else ifeq ($(SIM),vcs)
    VERILOG_SOURCES += $(WPWD)/../hdl/analog_probe_synopsys.sv
    ifeq ($(TOPLEVEL_LANG),verilog)
        VERILOG_SOURCES += $(WPWD)/../hdl/nettypes_pkg_synopsys.sv
        VERILOG_SOURCES += $(WPWD)/../hdl/rescap.sv
        VERILOG_SOURCES += $(WPWD)/../hdl/regulator.sv
        VERILOG_SOURCES += $(WPWD)/../hdl/tb_rescap.sv
        VERILOG_SOURCES += $(WPWD)/../hdl/tb_regulator.sv
    else ifeq ($(TOPLEVEL_LANG),vhdl)
        $(error VHDL toplevel not yet implemented)
        VHDL_SOURCES += $(WPWD)/../hdl/rescap.vhdl
        VHDL_SOURCES += $(WPWD)/../hdl/regulator.vhdl
    else
        $(error A valid value (verilog or vhdl) was not provided for TOPLEVEL_LANG=$(TOPLEVEL_LANG))
    endif
else
    $(error This example does not have support for SIM=$(SIM))
endif


# Options

COCOTB_HDL_TIMEUNIT=1ns
COCOTB_HDL_TIMEPRECISION=1ps

ifeq ($(SIM),$(filter $(SIM),ius xcelium))
    SIM_ARGS += -discipline logic
    SIM_ARGS += -amsconnrules ConnRules_full_fast
    SIM_ARGS += +dr_info
    SIM_ARGS += -iereport
    SIM_ARGS += -ieinfo
    SIM_ARGS += -ieinfo_log $(SIM_BUILD)/ams_ieinfo.log
    SIM_ARGS += -spectre_args "+lqtimeout 7200"
    SIM_ARGS += run.scs
    SIM_ARGS += $(EXTRA_SIM_ARGS)
else ifeq ($(SIM),vcs)
    COMPILE_ARGS += -ad=./vcsAD.init
    COMPILE_ARGS += -ams
    COMPILE_ARGS += -ams_iereport
    COMPILE_ARGS += -xlrm coerce_nettype
#    COMPILE_ARGS += -ams_discipline <discipline_name>
    SIM_ARGS += $(EXTRA_SIM_ARGS)
else
    $(error This example does not have support for SIM=$(SIM))
endif


include $(shell cocotb-config --makefiles)/Makefile.sim
