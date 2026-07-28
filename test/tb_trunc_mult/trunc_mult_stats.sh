#!/bin/bash

set -euo pipefail

for ((i = 0; i < 12; i++))
do
    echo "Drop bits = $i"
    declare -n curr_out="drop_bits_$i"
    TRUNC_DROP_BITS=$i yosys -l synth.log -c stat_trunc_mult.tcl > /dev/null 2>&1

    cell_count=$(awk '/Number of cells:/ {last = $NF} END {print last}' synth.log)
    total_area=$(awk '/Chip area/ {print $NF}' synth.log)

    # echo -e "Cells: $cell_count"
    # echo -e "Area: $total_area"

    curr_out+=("$cell_count" "$total_area")
    # printf '%s ' "${curr_out[@]}"

done

for ((i = 0; i < 12; i++))
do
    declare -n curr_out="drop_bits_$i"
    line="$(printf '%s,' "${curr_out[@]}")"
    echo "${line%,}"
done > yosys_stat.csv
