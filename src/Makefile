SIM ?= icarus
TOPLEVEL_LANG ?= verilog
VERILOG_SOURCES += trunc_mult.v
FST ?= -fst
COCOTB_TOPLEVEL = trunc_mult
COCOTB_TEST_MODULES = trunc_mult_tb

COCOTB_HDL_TIMEUNIT = 1ns
COCOTB_HDL_TIMEPRECISION = 1ps

WAVES=1

include $(shell cocotb-config --makefiles)/Makefile.sim