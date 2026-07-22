SIM ?= verilator
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../../src/
PROJECT_SOURCES = trunc_mult.v

SIM_BUILD = sim_build/rtl
VERILOG_SOURCES += $(addprefix $(SRC_DIR),$(PROJECT_SOURCES))
VERILOG_SOURCES += tb_trunc_mult.v

TOPLEVEL = tb_trunc_mult
COCOTB_TEST_MODULES = trunc_mult_tb
COMPILE_ARGS += -Wno-WIDTHEXPAND
EXTRA_ARGS += --trace --trace-structs

include $(shell cocotb-config --makefiles)/Makefile.sim