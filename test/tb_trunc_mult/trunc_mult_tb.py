import cocotb
from cocotb.triggers import Timer
import numpy as np
import os
import csv

TEST_SEED = int(os.getenv("FIR_TB_SEED", "12345"))
cocotb.log.info(f"FIR_TB_SEED={TEST_SEED}")

max_val = 2047
min_val = -2048
drop_bits_size = 12
data_width = 12
output_width = data_width * 2

@cocotb.test()
async def test_trunc_mult(dut):
    rng = np.random.default_rng(TEST_SEED)

    num_pairs = 25
    total_output_size = num_pairs * num_pairs

    a = rng.integers(low=min_val, high=max_val+1, size=num_pairs)
    b = rng.integers(low=min_val, high=max_val+1, size=num_pairs)

    golden_outputs = []
    trunc_outputs = [[] for _ in range(drop_bits_size)]

    for idx,i in enumerate(a):
        for j in b:
            dut.a.value = int(i) & 0x0FFF
            dut.b.value = int(j) & 0x0FFF

            await Timer(5, "ns")

            for k in range(drop_bits_size):
                curr_trunc_out = dut.trunc_out[k].value.to_signed()
                trunc_outputs[k].append(curr_trunc_out)

            golden_out = dut.golden_ref.value.to_signed()
            golden_outputs.append(golden_out)

    curr_gold_shift = []
    
    for i in range(drop_bits_size):
        curr_trunc_out = trunc_outputs[i]
        curr_gold_shift = [golden_outputs[j] >> i for j in range(total_output_size)]

        for j in range(total_output_size):
            assert abs(curr_trunc_out[j] - curr_gold_shift[j]) <= 2, f"error too large between trunc={curr_trunc_out[j]} and gold={curr_gold_shift[j]}"


    trunc_error_per_drop = [[] for _ in range(drop_bits_size)]

    for i in range(drop_bits_size):
        curr_trunc_out = trunc_outputs[i]
        curr_gold_shift = [golden_outputs[j] >> i for j in range(total_output_size)]

        for j in range(total_output_size):
            error = abs((curr_trunc_out[j] - curr_gold_shift[j]) << i)
            trunc_error_per_drop[i].append(error)

    with open("trunc_error.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(trunc_error_per_drop)



        
        

