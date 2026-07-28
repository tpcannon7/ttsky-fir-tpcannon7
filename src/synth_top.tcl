set LIB_PATH "$::env(HOME)/.ciel/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"

yosys read_verilog trunc_mult.v tt_um_tpcannon7_fir.v spi.v control.v fir_filter.v
yosys read_liberty -lib $LIB_PATH
yosys hierarchy -check -top tt_um_tpcannon7_fir
yosys synth -top tt_um_tpcannon7_fir
yosys dfflibmap -liberty $LIB_PATH
yosys abc -liberty $LIB_PATH
yosys clean
yosys stat -liberty $LIB_PATH
