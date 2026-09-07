set OUT_DIR ./outputs

set_db init_lib_search_path $env(GPDK_LIB_PATH)
set_db init_hdl_search_path ../src/

read_libs $env(GPDK_LIB_PATH)/slow_vdd1v0_basicCells.lib

read_hdl -sv {
    tt_um_tpcannon7_fir_.v \
    trunc_mult.v \
    spi.v \
    fir_filter.v \
    control.v \
}

elaborate tt_um_tpcannon7_fir

read_sdc contraints.sdc

init_design

syn_generic
syn_map
syn_opt

write_hdl > $(OUT_DIR)/d_fir_netlist.v

report_gates $(OUT_DIR)/gates.rpt
report_timing $(OUT_DIR)/timing.rpt
report_summary $(OUT_DIR)/summary.rpt