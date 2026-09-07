set OUT_DIR ./impl_outputs
set TECH_LEF /home/net/local/gsclib045_all_v4.7/gsclib045/lef/gsclib045_tech.lef
set MACRO_LEF /home/net/local/gsclib045_all_v4.7/gsclib045/lef/gsclib045_macro.lef

set init_verilog ./synth_outputs/d_fir_netlist.v
set init_design_netlisttype {Verilog}

set init_lef_file [list \
    $TECH_LEF \
    $MACRO_LEF \
]

set init_pwr_nets VDD
set init_gnd_nets VSS

set init_mmmc_file ./mmmc.tcl

init_design

# floorplan + i/o


# power planning

# placement

# CTS

# routing

# GDS?
