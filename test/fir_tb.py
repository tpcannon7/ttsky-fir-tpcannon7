import cocotb
from cocotb.triggers import RisingEdge, Timer
from cocotb.clock import Clock

from scipy.signal import firwin, lfilter
import numpy as np

# params
taps = 8
coeff_width = 8
sample_width = 8
out_width = 8 # can be chanegd to 16

# signed binary to signed decimal
def to_decimal(num, bits):
    assert len(num) <= bits
    n = int(num, 2)
    s = 1 << (bits - 1)
    return (n & (s - 1)) - (n & s)

async def reset(dut):
    dut.ena.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0

    dut.rst_n.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)

    dut.rst_n.value = 1

@cocotb.test()
async def test_fir(dut):
    clk = Clock(dut.clk, 10, "ns")
    clk.start()

    await reset(dut)
    dut.ena.value = 1


