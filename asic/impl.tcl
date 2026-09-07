set OUT_DIR ./impl_outputs
set TECH_LEF /home/net/local/gsclib045_all_v4.7/gsclib045/lef/gsclib045_tech.lef
set MACRO_LEF /home/net/local/gsclib045_all_v4.7/gsclib045/lef/gsclib045_macro.lef
set GDS_PATH /home/net/local/gsclib045_all_v4.7/gsclib045/gds/gsclib045.gds
set MAP_PATH /home/net/local/gpdk045_v_6_0/soce/streamOut.map

setDesignMode -process 45

set init_verilog ./synth_outputs/d_fir_netlist.v
set init_design_netlisttype {Verilog}

set init_lef_file [list \
    $TECH_LEF \
    $MACRO_LEF \
]

set init_pwr_net { VDD! }
set init_gnd_net { VSS! }

set init_mmmc_file ./mmmc.tcl

setGenerateViaMode -auto true

init_design

# BUFX2 uses CoreSiteDouble; adding rows with CoreSiteDouble causes shorts on Metal1
# disallow usage and use other buffers that are CoreSite
setDontUse BUFX2 true

# floorplan + i/o
floorplan -site CoreSite -su 1.0 0.7 4.0 4.0 4.0 4.0

globalNetConnect VDD! -type pgpin -pin VDD -inst * -verbose
globalNetConnect VSS! -type pgpin -pin VSS -inst * -verbose

setPinAssignMode -pinEditInBatch true
editPin -fixOverlap 1 -layer 5 -spreadDirection clockwise -side LEFT -spreadType SIDE \
    -spacing 2.0 -pin {clk rst_n ena ui_in[0] ui_in[1] ui_in[2] ui_in[3] ui_in[4] ui_in[5] ui_in[6] ui_in[7] \
                        uio_in[0] uio_in[1] uio_in[2] uio_in[3] uio_in[4] uio_in[5] uio_in[6] uio_in[7]}
editPin -fixOverlap 1 -layer 6 -spreadDirection clockwise -side RIGHT -spreadType SIDE \
    -spacing 2.0 -pin {uo_out[0] uo_out[1] uo_out[2] uo_out[3] uo_out[4] uo_out[5] uo_out[6] uo_out[7] \ 
                        uio_out[0] uio_out[1] uio_out[2] uio_out[3] uio_out[4] uio_out[5] uio_out[6] uio_out[7] \
                        uio_oe[0] uio_oe[1] uio_oe[2] uio_oe[3] uio_oe[4] uio_oe[5] uio_oe[6] uio_oe[7]}
setPinAssignMode -pinEditInBatch false
legalizePin

# power planning
addRing -nets {VDD! VSS!} -width 0.6 -spacing 0.5 \
    -layer [list top 7 bottom 7 left 6 right 6]
addStripe -nets {VDD! VSS!} -layer 6 -direction vertical \
    -width 0.4 -spacing 0.5 -set_to_set_distance 5 -start 0.5
setAddStripeMode -stacked_via_bottom_layer 6 \
    -stacked_via_top_layer 7
addStripe -nets {VDD! VSS!} -layer 7 -direction horizontal \
    -width 0.4 -spacing 0.5 -set_to_set_distance 5 -start 0.5

sroute -nets {VDD! VSS!}

# placement
place_opt_design

checkPlace ./impl_outputs/check_place.rpt

# CTS
ccopt_design

# check timing then optimize
timeDesign -postCTS -outDir ./impl_outputs/postcts_setup
timeDesign -postCTS -hold -outDir ./impl_outputs/postcts_hold
# setup then hold
optDesign -postCTS
optDesign -postCTS -hold

suspend

# routing
routeDesign

setAnalysisMode -analysisType onChipVariation -cppr both

# post-route timing check, then optimize
timeDesign -postRoute -outDir ./impl_outputs/postroute_setup
timeDesign -postRoute -hold -outDir ./impl_outputs/postroute_hold
optDesign -postRoute -setup -hold
optDesign -postRoute -drv

# add fillers
addFiller -cell FILL1 FILL2 FILL4 FILL8 FILL16 FILL32 FILL64 -prefix FILL -fitGap
addFiller -cell DECAP2 DECAP3 DECAP4 DECAP5 DECAP6 DECAP7 DECAP8 DECAP9 DECAP10 -prefix DECAP -fitGap

# ecoRoute after adding fillers to fix any issues
ecoRoute -target

suspend

# reporting
clearDrc
verify_drc -report ./impl_outputs/drc.rpt
verifyConnectivity -report ./impl_outputs/connect.rpt
checkPlace ./impl_outputs/post_route_check_place.rpt

timeDesign -postRoute -outDir ./impl_outputs/final_setup
timeDesign -postRoute -hold -outDir ./impl_outputs/final_hold

setAnalysisMode -checkType setup
report_timing > ./impl_outputs/setup.rpt
report_constraint -all_violators > setup_checks.rpt

setAnalysisMode -checkType hold
report_timing > ./impl_outputs/hold.rpt
report_constraint -all_violators > hold_checks.rpt

report_area -detail > ./impl_outputs/area.rpt
report_power -hierarchy all -outfile ./impl_outputs/power.rpt

# write outputs
saveNetlist ./impl_outputs/d-fir_gpdk045_pnr_netlist.v
streamOut ./impl_outputs/d-fir_gpdk045.gds \
    -mapFile $MAP_PATH \
    -merge [list $GDS_PATH] \
    -libName DesignLib \
    -structureName tt_um_tpcannon7_fir \
    -units 2000 \
    -mode ALL

