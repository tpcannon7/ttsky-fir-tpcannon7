SIM ?= icarus
TOPLEVEL_LANG ?= verilog
FST ?= -fst
VERILOG_SOURCES += spi.v
COCOTB_TOPLEVEL = spi
COCOTB_TEST_MODULES = spi_tb

COCOTB_HDL_TIMEUNIT = 1ns
COCOTB_HDL_TIMEPRECISION = 1ps

WAVES=1

include $(shell cocotb-config --makefiles)/Makefile.sim