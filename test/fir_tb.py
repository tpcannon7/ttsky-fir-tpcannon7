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

# clock perod (ns)
clock_period = 40

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
LOAD_EN = 0x01
IN_VALID = 0x02
OUT_READY = 0x04
IN_READY = 0x08
OUT_VALID = 0x10
BYTE_EN = 0x20

async def cycle_counter(dut):
    global global_cycles
    while True:
        await RisingEdge(dut.clk)
        global_cycles += 1

async def reset(dut):
    dut.ui_in.value = 0x00
    dut.uio_in.value = 0x00
    dut.ena.value = 1
    dut.rst_n.value = 0

    await ClockCycles(dut.clk, 50)
    dut.rst_n.value = 1

    await RisingEdge(dut.clk)

async def load_coeff(dut, coeffs):
    if (coeff_width == 8):
        for coeff in coeffs:
            dut.uio_in.value = LOAD_EN | IN_VALID
            dut.ui_in.value = coeff

            # wait for in_ready
            await RisingEdge(dut.clk)
            while((dut.uio_out.value.to_unsigned() & IN_READY) == 0):
                    await RisingEdge(dut.clk)

        dut.uio_in.value = 0x00
        await RisingEdge(dut.clk)

    elif(coeff_width == 16):
        for coeff in coeffs:
            coeff_low = coeff & 0x00ff
            coeff_high = (coeff & 0xff00) >> 8

            dut.uio_in.value = LOAD_EN | IN_VALID
            dut.ui_in.value = coeff_low

            # wait in_ready, low_byte
            await RisingEdge(dut.clk)
            while((dut.uio_out.value.to_unsigned() & IN_READY) == 0):
                #cocotb.log.info("waiting low byte coeff")
                await RisingEdge(dut.clk)

            dut.uio_in.value = LOAD_EN | IN_VALID | BYTE_EN
            dut.ui_in.value = coeff_high

            # wait for in_ready, high byte
            await RisingEdge(dut.clk)
            while((dut.uio_out.value.to_unsigned() & IN_READY) == 0):
                #cocotb.log.info("waiting low byte coeff")
                await RisingEdge(dut.clk)
        
        dut.uio_in.value = 0x00
        await RisingEdge(dut.clk)

async def load_sample(dut, sample):
    if (sample_width == 8):
        dut.uio_in.value = IN_VALID
        dut.ui_in.value = sample
        await RisingEdge(dut.clk)
        dut.uio_in.value = 0x00
    elif (sample_width == 16):
        sample_low = sample & 0x00ff
        sample_high = (sample & 0xff00) >> 8

        # assert in_valid, send low byte of sample
        dut.uio_in.value = IN_VALID
        dut.ui_in.value = sample_low
        
        # wait for in_ready to send next byte
        await RisingEdge(dut.clk)
        while((dut.uio_out.value.to_unsigned() & IN_READY) == 0):
            #cocotb.log.info("waiting low byte sample")
            await RisingEdge(dut.clk)

        dut.uio_in.value = IN_VALID | BYTE_EN
        dut.ui_in.value = sample_high

        # wait for in_ready, high_byte
        await RisingEdge(dut.clk)
        while((dut.uio_out.value.to_unsigned() & IN_READY) == 0):
            #cocotb.log.info("waiting high byte sample")
            await RisingEdge(dut.clk)

        dut.ui_in.value = 0x00
        dut.uio_in.value = 0x00
        await RisingEdge(dut.clk)

async def read_output(dut):
    if (sample_width == 8):
        dut.uio_in.value = OUT_READY

        await RisingEdge(dut.clk)
        while((dut.uio_out.value.to_unsigned() & OUT_VALID) == 0):
            #cocotb.log.info("waiting output")
            await RisingEdge(dut.clk)

        out = dut.uo_out.to_unsigned()
        dut.uio_out.value = 0x00
        return out
    elif (sample_width == 16):
        dut.uio_in.value = OUT_READY

        # wait for out_valid, low byte
        await RisingEdge(dut.clk)
        while((dut.uio_out.value.to_unsigned() & OUT_VALID) == 0):
            #cocotb.log.info("waiting low byte output")
            await RisingEdge(dut.clk)

        out_low = dut.uo_out.value.to_unsigned()
        dut.uio_in.value = OUT_READY

        # wait for out_valid, high byte
        await RisingEdge(dut.clk)
        while((dut.uio_out.value.to_unsigned() & OUT_VALID) == 0):
            #cocotb.log.info("waiting high byte output")
            await RisingEdge(dut.clk)

        out_high = dut.uo_out.value.to_unsigned()
        dut.uio_in.value = 0x00

        await RisingEdge(dut.clk)

        result = ((out_high & 0xff) << 8) | (out_low & 0xff)
        if result & 0x8000:
            result -= 0x10000
        return result

@cocotb.test()
async def test_impulse_response(dut):
    clk = Clock(dut.clk, clock_period, "ns")
    cocotb.start_soon(clk.start())

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
    await load_coeff(dut, coeffs)

    for idx, s in enumerate(samples):
        # assert in_valid, load sample in
        await load_sample(dut, s)
        await RisingEdge(dut.clk)
        cocotb.log.info(f"sample {idx} = {s}")  

        # read output
        res = await read_output(dut)
        await RisingEdge(dut.clk)
        cocotb.log.info(f"res = {res}")
        cocotb.log.info(f"expected = {coeffs[idx]}")
        assert abs(res - coeffs[idx]) <= 5, f"{res} does not match in acceptable range to {coeffs[idx]}"

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
    ts = np.linspace(0, 5, 100)
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

@cocotb.test()
async def test_reset_mid_sequence(dut):
    pass

@cocotb.test()
async def test_load_mid_sequence(dut):
    pass
