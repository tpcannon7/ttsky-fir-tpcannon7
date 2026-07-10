import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, Timer, ReadOnly, ClockCycles
from cocotb.clock import Clock
from scipy.signal import firwin, lfilter, chirp, freqz
import numpy as np
import matplotlib.pyplot as plt
import math


# TODO: add more tests!
# reset during compute
# check loading during compute/mid input?
# need more tests for TEST state with static test vectors on chip

# coeffs now load in same shift fashion as with the sampling
# load N tap coeffcients first and tap 0 coeffcients last

#TODO: umm find out to make sclk work on uio_in? check spi shit actually works too
# i added a basic control layer that should work on the fir filter? double check that too!

# clock perod (ns)
clock_period = 40
spi_clock = 1000
spi_frame_len = 16

# params
taps = 16
coeff_width = 16
sample_width = 16

# max/min values for bit widths
min_val = -(2**(coeff_width-1))
max_val = (2**(coeff_width-1)-1)
normalize = ((2**(coeff_width-1)))

# Hz
fc = 10000
# 21 cycles for 16 taps, 13 for 8 taps (taps + 5 = comp time + byte handling)
fs = (1 / (clock_period * 1e-9)) / (taps + 5) 

global_cycles = 0
output_done_cycles = []

# bidirect pins
CS_N = 0x01
MOSI = 0x02
MISO = 0x04
SCLK = 0x08

async def cycle_counter(dut):
    global global_cycles
    while True:
        await RisingEdge(dut.clk)
        global_cycles += 1

async def reset(dut):
    dut.ui_in.value = 0x80
    dut.uio_in.value = CS_N | MOSI
    dut.ena.value = 1
    dut.rst_n.value = 0

    await ClockCycles(dut.clk, 50)
    dut.rst_n.value = 1

    await RisingEdge(dut.clk)

async def generate_sclk(dut, period_ns, bit_index=3):
    # Ensure initial state is clean
    current_val = int(dut.uio_in.value) if dut.uio_in.value.is_resolvable else 0
    while True:
        # Driving Low
        dut.uio_in.value = current_val & ~(1 << bit_index)
        await Timer(period_ns / 2, units='ns')

        # Driving High
        dut.uio_in.value = current_val | (1 << bit_index)
        await Timer(period_ns / 2, units='ns')

async def spi_tx(dut, data_in, sclk):
    dut.cs_n.value = 0
    await RisingEdge(dut.clk)
    cocotb.start_soon(sclk.start())
    for i in range(spi_frame_len):
        dut.mosi.value = (data_in & 0x8000) >> (spi_frame_len - 1)
        await RisingEdge(dut.sclk)
        data_in = data_in << 1

    await FallingEdge(dut.sclk)
    sclk.stop()
    
    dut.cs_n.value = 1
    await ClockCycles(dut.clk, 25)

async def spi_rx(dut):
    rx_data = 0x0000
    for i in range(spi_frame_len):
        await RisingEdge(dut.sclk)
        out = int(dut.uio_in[2].value)

async def spi_transact(dut, tx_data, sclk):
    tx = cocotb.start_soon(spi_tx(dut,tx_data,sclk))
    rx = cocotb.start_soon(spi_rx(dut))

    await Combine(tx,rx)

async def load_coeff(dut, coeffs, sclk):
    for coeff in coeffs[::-1]:
        dut.ui_in.value = 0x00
        await spi_transact(dut, coeff, sclk)

async def load_sample(dut, sample, sclk):
    dut.ui_in.value = 0x80
    await spi_transact(dut,sample,sclk)

@cocotb.test()
async def test_impulse_response(dut):
    clk = Clock(dut.clk, clock_period, "ns")
    cocotb.start_soon(clk.start())
    sclk = Clock(cocotb.handle[uio_in[3]], spi_clock, "ns")

    h = firwin(taps, fc, fs=fs)
    cocotb.log.info(f"float coeffs = {h}")

    coeffs = h * normalize
    coeffs = [max(min_val, min(max_val, int(round(c)))) for c in coeffs]
    cocotb.log.info(f"fixed coeffs = {coeffs}")

    samples = [(2**(sample_width-1))-1] + ([0] * (taps - 1))

    cocotb.log.info("----------------------------------")
    cocotb.log.info("         IMPULSE RESPONSE         ")
    cocotb.log.info("----------------------------------")

    await reset(dut)
    await load_coeff(dut, coeffs, sclk)

    for idx, s in enumerate(samples):
        # assert in_valid, load sample in
        await load_sample(dut, s, sclk)
        await RisingEdge(dut.clk)
        cocotb.log.info(f"sample {idx} = {s}")  

        # read output
        # res = await read_output(dut)
        # await RisingEdge(dut.clk)
        # cocotb.log.info(f"res = {res}")
        # cocotb.log.info(f"expected = {coeffs[idx]}")
        # assert abs(res - coeffs[idx]) <= 5, f"{res} does not match in acceptable range to {coeffs[idx]}"

@cocotb.test()
async def test_step_response(dut):
    clk = Clock(dut.clk, clock_period, "ns")
    cocotb.start_soon(clk.start())

    # generate coeffs
    h = firwin(taps, fc, fs=fs)
    cocotb.log.info(f"float coeffs = {h}")
    
    # fixed point
    coeffs = h * normalize
    coeffs = [max(min_val, min(max_val, int(round(c)))) for c in coeffs]
    cocotb.log.info(f"fixed coeffs = {coeffs}")

    # step response
    samples = [0] * taps + [(2**(sample_width-1))-1] * taps

    cocotb.log.info("----------------------------------")
    cocotb.log.info("           STEP RESPONSE          ")
    cocotb.log.info("----------------------------------")

    await reset(dut)
    await load_coeff(dut, coeffs)

    out = 0

    for idx, s in enumerate(samples):
        # load sample in
        await load_sample(dut, s)
        cocotb.log.info(f"sample {idx} = {s}")

        # take sample out
        out = await read_output(dut)   

    expected = sum(coeffs)
    cocotb.log.info(f"out = {out}")
    cocotb.log.info(f"exp = {expected}")

    assert abs(out - expected) <= 20, f"{out} does not match within error to {expected}"
    
@cocotb.test()
async def test_noisy_sine(dut):
    clk = Clock(dut.clk, clock_period, "ns")
    cocotb.start_soon(clk.start())

    cocotb.start_soon(cycle_counter(dut))

    # generate coeffs
    h = firwin(taps, fc, fs=fs)
    cocotb.log.info(f"float coeffs = {h}")
    
    # fixed point
    coeffs = h * normalize
    coeffs = [max(min_val, min(max_val, int(round(c)))) for c in coeffs]
    cocotb.log.info(f"fixed coeffs = {coeffs}")

    # sine wave + noise (1 KHz)
    duration = 0.001
    n_samples = int(fs * duration)
    ts = np.linspace(0,duration,n_samples, endpoint=False)
    ys = np.sin(2*np.pi * 1000.0 * ts)
    yerr = 0.5 * np.random.normal(size=len(ts))
    yraw = ys + yerr

    y_dut = []
    samples = yraw * normalize
    samples = [max(min_val, min(max_val, int(round(s)))) for s in samples]

    # "true" filter
    samples_float = [s / float(normalize) for s in samples]
    y_lfilter = lfilter(h, 1.0, samples_float)

    cocotb.log.info("----------------------------------")
    cocotb.log.info("           NOISY SINE             ")
    cocotb.log.info("----------------------------------")

    await reset(dut)
    await load_coeff(dut, coeffs)

    for idx, s in enumerate(samples):
        # input sample
        await load_sample(dut, s)
        cocotb.log.info(f"sample {idx} = {s}")

        out = await read_output(dut)
        output_done_cycles.append(global_cycles)

        cocotb.log.info(f"out = {out}")
        out = out / float(normalize)
        y_dut.append(out)

    plt.plot(ts, yraw, 'k-')
    plt.plot(ts, y_lfilter, 'r-')
    plt.plot(ts, y_dut, 'c-')
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.title("Noisy Sinusoid Filtering, DUT vs. Python model")
    plt.legend(["raw","python filter", "dut filter"])
    plt.savefig('noisy_sine_comparison.png')

    gold_rms = math.sqrt(sum(x**2 for x in y_lfilter) / len(y_lfilter))
    dut_rms = math.sqrt(sum(x**2 for x in y_dut) / len(y_dut))
    err_rms = math.sqrt(sum((g - d)**2 for g, d in zip(y_lfilter, y_dut)) / len(y_dut))
    snr = 20.0 * math.log10(gold_rms / err_rms)

    assert snr > 30.0, f"SNR = {snr} below acceptable threshold"
    cocotb.log.info(f"SNR = {snr}")

@cocotb.test()
async def test_switching_inputs(dut):
    clk = Clock(dut.clk, clock_period, "ns")
    cocotb.start_soon(clk.start())

    # generate coeffs
    h = firwin(taps, fc, fs=fs)
    cocotb.log.info(f"float coeffs = {h}")
    
    # fixed point
    coeffs = h * normalize
    coeffs = [max(min_val, min(max_val, int(round(c)))) for c in coeffs]
    cocotb.log.info(f"fixed coeffs = {coeffs}")

    samples = [max_val if i % 2 == 0 else min_val for i in range(taps*2)]
    cocotb.log.info(f"samples = {samples}")

    cocotb.log.info("----------------------------------")
    cocotb.log.info("         SWITCHING INPUTS         ")
    cocotb.log.info("----------------------------------")

    await reset(dut)
    await load_coeff(dut, coeffs)

    outputs = []

    for idx, s in enumerate(samples):
        await load_sample(dut, s)
        cocotb.log.info(f"sample {idx} = {s}")

        o = await read_output(dut)
        cocotb.log.info(f"out = {o}")
        cocotb.log.info(f"float out = {o / float(normalize)}")
        outputs.append(o)

    output_diff = np.diff(outputs)
    cocotb.log.info(f"output diffs = {output_diff}")

    assert (np.all(output_diff[taps:] == 0)), f"output diff unexpected nonzero during switching"


# this isnt a real test but more to verify the plots match closely
@cocotb.test()
async def test_frequency_response(dut):
    clk = Clock(dut.clk, clock_period, "ns")
    cocotb.start_soon(clk.start())

    await reset(dut)

    # generate coeffs
    h = firwin(taps, fc, fs=fs)
    cocotb.log.info(f"float coeffs = {h}")
    
    # fixed point
    coeffs = h * normalize
    coeffs = [max(min_val, min(max_val, int(round(c)))) for c in coeffs]
    coeffs = [c / float(normalize) for c in coeffs]

    w_dut, h_dut = freqz(coeffs, 1.0, fs=fs)
    w_true, h_true = freqz(h, 1.0, fs=fs)

    cocotb.log.info("----------------------------------")
    cocotb.log.info("         FREQUENCY RESPONSE       ")
    cocotb.log.info("----------------------------------")

    plt.title("Frequency Response of DUT vs. Python Model")
    plt.plot(w_dut, 20*np.log10(abs(h_dut)), 'r-')
    plt.plot(w_true, 20*np.log10(abs(h_true)), 'c-' )
    plt.axvline(fc, color='black', linestyle=':', linewidth=0.8)
    plt.ylabel("Amplitude (dB)")
    plt.xlabel("Frequency (Hz)")
    plt.legend(["dut freq resp", "true freq response"])
    plt.savefig('freq_response.png')


# test to verify new coeff shift reg works properly
@cocotb.test()
async def test_non_symmetric_coeff(dut):
    clk = Clock(dut.clk, clock_period, "ns")
    cocotb.start_soon(clk.start())

    coeffs = [(i+1) / taps for i in range(taps)]
    cocotb.log.info(f"coeffs = {coeffs}")

    coeffs = [c * normalize for c in coeffs]
    coeffs = [max(min_val, min(max_val, int(round(c)))) for c in coeffs]
    cocotb.log.info(f"fixed coeffs = {coeffs}")

    samples = [(2**(sample_width-1))-1] + ([0] * (taps - 1))

    await reset(dut)
    await load_coeff(dut, coeffs)

    outputs = []

    for idx, s in enumerate(samples):
        await load_sample(dut, s)
        cocotb.log.info(f"sample {idx} = {s}")

        out = await read_output(dut)
        cocotb.log.info(f"out = {out}")

        expected = coeffs[idx]

        assert abs(out-expected) <= 10, f"{out} != {expected}, order incorrect"


@cocotb.test()
async def test_on_chip_test_mode(dut):
    clk = Clock(dut.clk, clock_period, "ns")
    cocotb.start_soon(clk.start())

    await reset(dut)

# @cocotb.test()
# async def test_reset_mid_sequence(dut):
#     pass

# @cocotb.test()
# async def test_load_mid_sequence(dut):
#     pass


# @cocotb.test()
# async def test_full_handshake_no_helpers(dut):
#     pass