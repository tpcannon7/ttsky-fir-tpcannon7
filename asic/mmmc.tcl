# set libs
set QX_TECH_FILE /home/net/local/gsclib045_all_v4.7/gsclib045/qrc/qx/gpdk045.tch
set GPDK_LIB_PATH /home/net/local/gsclib045_all_v4.7/gsclib045/timing
set SS_LIB_PATH $GPDK_LIB_PATH/slow_vdd1v0_basicCells.lib
set FF_LIB_PATH $GPDK_LIB_PATH/fast_vdd1v0_basicCells.lib

create_library_set -name SS_LIB -timing $SS_LIB_PATH
create_library_set -name FF_LIB -timing $FF_LIB_PATH

create_constraint_mode -name SDC -sdc_files ./d-fir.sdc

# 25 is default it seems?
create_rc_corner -name TT_RC -qx_tech_file $QX_TECH_FILE -T 25

# operating conditions for lib
create_op_cond -name SS_OP_COND -library_file $SS_LIB_PATH -P 1 -V 0.9 -T 125
create_op_cond -name FF_OP_COND -library_file $FF_LIB_PATH -P 1 -V 1.1 -T 0

# corners
create_delay_corner -name FF_CNR -library_set FF_LIB -opcond FF_OP_COND -rc_corner TT_RC
create_delay_corner -name SS_CNR -library_set SS_LIB -opcond SS_OP_COND -rc_corner TT_RC

# setup matters more for slow corners
create_analysis_view -name SETUP -constraint_mode SDC -delay_corner SS_CNR
# hold matters more for fast corners
create_analysis_view -name HOLD -constraint_mode SDC -delay_corner FF_CNR

set_analysis_view -hold HOLD -setup SETUP
