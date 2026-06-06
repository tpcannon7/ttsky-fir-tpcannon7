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

    fs = 10000
    t = np.linspace(0, 1, fs)
    signal = np.sin(2 * np.pi * 500 * t) # 500 hz sine wave
    noise = np.random.randn(len(t)) * 0.3 # noise
    coeffs = np.array([16] * 8, dtype=float)
    input_signal = signal + noise
    reference = lfilter(coeffs, 1.0, input_signal)

    samples = (np.sin(2 * np.pi * 0.05 * np.arange(100)) * 50).astype(int)

    await reset(dut)
    dut.ena.value = 1
        
    for i, sample in enumerate(samples):
        # sample is already an integer, just write it
        dut.ui_in.value = int(sample) & 0xFF  # mask to 8 bits handles negative numbers
        await RisingEdge(dut.clk)
        # read output - handle signed
        raw = int(dut.tt_um_tpcannon7_fir.fir.out_full.value.to_signed())

        cocotb.log.info(f"sample = {sample} dut = {raw/64} ref = {reference[i]:.1f}")


