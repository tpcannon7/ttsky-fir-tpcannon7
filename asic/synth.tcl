set OUT_DIR ./synth_outputs
set GPDK_LIB_PATH /home/net/local/gsclib045_all_v4.7/gsclib045/timing

set_db init_lib_search_path $GPDK_LIB_PATH
set_db init_hdl_search_path ../src/

read_libs $GPDK_LIB_PATH/slow_vdd1v0_basicCells.lib

read_hdl -sv [list \
    "tt_um_tpcannon7_fir.v" \
    "trunc_mult.v" \
    "spi.v" \
    "fir_filter.v" \
    "control.v" \
]

elaborate tt_um_tpcannon7_fir

read_sdc ./d-fir.sdc

init_design

syn_generic
syn_map
syn_opt

write_hdl > $OUT_DIR/d_fir_netlist.v

report_gates tt_um_tpcannon7_fir > $OUT_DIR/gates.rpt
report_timing > $OUT_DIR/timing.rpt
report_qor tt_um_tpcannon7_fir > $OUT_DIR/qor.rpt
report_area tt_um_tpcannon7_fir > $OUT_DIR/area.rpt