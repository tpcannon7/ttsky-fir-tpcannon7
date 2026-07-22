#!/usr/bin/env python3

import matplotlib.pyplot as plt
import csv
import numpy as np
import os

DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "docs")
trunc_error_csv = "trunc_error.csv"
drop_bits_size = 12
num_pairs = 25
total_output_size = num_pairs * num_pairs

yosys_stat_csv = "yosys_stat.csv"

def parse_trunc_error_csv():
    max_abs_error_per_drop_bit = [0 for _ in range(drop_bits_size)]
    mean_abs_error_per_drop_bit = [0 for _ in range(drop_bits_size)]

    with open(trunc_error_csv, mode='r', newline="", encoding='utf-8') as file:
        reader = csv.reader(file)
        for idx, row in enumerate(reader):
            curr_max_error = 0
            sum_error = 0
            for i in range(total_output_size):
                if int(row[i]) > curr_max_error:
                    curr_max_error = int(row[i])
                sum_error += int(row[i])

            max_abs_error_per_drop_bit[idx] = curr_max_error
            mean_abs_error_per_drop_bit[idx] = sum_error / float(total_output_size)

    print(max_abs_error_per_drop_bit)
    print(mean_abs_error_per_drop_bit)

    return max_abs_error_per_drop_bit, mean_abs_error_per_drop_bit
                
def parse_yosys_stats():
    yosys_stats_per_drop_bit = [[] for _ in range(drop_bits_size)]

    with open(yosys_stat_csv, 'r', newline="", encoding='utf-8') as file:
        reader = csv.reader(file)

        for idx, row in enumerate(reader):
            for col in row:
                yosys_stats_per_drop_bit[idx].append(float(col))

    print(yosys_stats_per_drop_bit)

    return yosys_stats_per_drop_bit

def generate_plots(max_abs_error, mean_abs_error, yosys_stats):
    x = np.arange(drop_bits_size)

    cells = [row[0] for row in yosys_stats]
    area = [row[1] for row in yosys_stats]

    fig, (ax_err, ax_area) = plt.subplots(2, 1, sharex=True, figsize=(6.4, 4.8))
    fig.suptitle("12×12 Truncated Multiplier Area–Error Tradeoff (Sky130A HD)", fontweight='bold')

    ax_err.plot(x, max_abs_error, 'b-', linewidth=1.5, label='max |error|')
    ax_err.plot(x, mean_abs_error, 'b--', linewidth=1.5, label='mean |error|')
    ax_err.set_ylabel('|Error| (full-precision LSBs)')
    ax_err.legend()
    ax_err.grid(True, alpha=0.3)
    ax_err.axvline(x=8, linestyle='--', color='gray', alpha=0.7)

    ax_area.plot(x, cells, 'r-', linewidth=1.5, label='cells')
    ax_area.set_xlabel('DropBits')
    ax_area.set_ylabel('Area (cells)')
    ax_area.grid(True, alpha=0.3)
    ax_area.axvline(x=8, linestyle='--', color='gray', alpha=0.7)

    ax_area2 = ax_area.twinx()
    ax_area2.plot(x, area, 'g--', linewidth=1.5, label='µm²')
    ax_area2.set_ylabel('Area (µm²)')

    lines1, labels1 = ax_area.get_legend_handles_labels()
    lines2, labels2 = ax_area2.get_legend_handles_labels()
    ax_area.legend(lines1 + lines2, labels1 + labels2, loc='best')

    plt.tight_layout()
    fig.savefig(os.path.join(DOCS_DIR, "trunc_mult_tradeoff.png"))


    

def main():
    max_abs_error, mean_abs_error =  parse_trunc_error_csv()
    yosys_stats = parse_yosys_stats()
    generate_plots(max_abs_error, mean_abs_error, yosys_stats)



if __name__ == "__main__":
    main()