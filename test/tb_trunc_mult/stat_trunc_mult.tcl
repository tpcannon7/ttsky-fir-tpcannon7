set DROP_BITS $::env(TRUNC_DROP_BITS)
set DATA_WIDTH 12

set LIB_PATH "$::env(HOME)/.ciel/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"

yosys read_verilog -defer ../../src/trunc_mult.v
yosys chparam -set DataWidth $DATA_WIDTH -set DropBits $DROP_BITS
yosys read_liberty -lib $LIB_PATH
yosys hierarchy -check -top trunc_mult
yosys synth -top trunc_mult
yosys abc -liberty $LIB_PATH
yosys clean
yosys stat -liberty $LIB_PATH