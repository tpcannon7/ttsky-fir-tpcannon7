import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, Timer, ReadOnly, ClockCycles
from cocotb.clock import Clock
from scipy.signal import firwin, lfilter
import numpy as np
import matplotlib.pyplot as plt
import math


# TODO: add more tests!
# reset during compute
# verify handshake works by streaming inputs

# params
taps = 8
coeff_width = 16
sample_width = 16

min_val = -(2**(coeff_width-1))
max_val = (2**(coeff_width-1)-1)
normalize = ((2**(coeff_width-1)))

# Hz
fc = 10000
fs = 32000

# bidirect pins
LOAD_EN = 0x01
IN_VALID = 0x02
OUT_READY = 0x04
IN_READY = 0x08
OUT_VALID = 0x10
BYTE_EN = 0x20

async def reset(dut):
    dut.ui_in.value = 0x00
    dut.uio_in.value = 0x00
    dut.ena.value = 1
    dut.rst_n.value = 0

    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1

    await RisingEdge(dut.clk)

async def load_coeff(dut, coeffs):
    if (coeff_width == 8):
        # assert load_en
        dut.uio_in.value = LOAD_EN

        # wait for in_ready
        while((dut.uio_out.value.to_unsigned() & IN_READY) == 0):
                await RisingEdge(dut.clk)

        # assert in_valid + load_en, then load coeffcients
        dut.uio_in.value = LOAD_EN | IN_VALID
        for coeff in coeffs:
            dut.ui_in.value = coeff
            await RisingEdge(dut.clk)

        dut.uio_in.value = 0x00
        await RisingEdge(dut.clk)
    elif(coeff_width == 16):
        dut.uio_in.value = LOAD_EN

        while((dut.uio_out.value.to_unsigned() & IN_READY) == 0):
            await RisingEdge(dut.clk)

        for coeff in coeffs:
            dut.uio_in.value = LOAD_EN | IN_VALID
            coeff_low = coeff & 0x00ff
            coeff_high = (coeff & 0xff00) >> 8

            dut.ui_in.value = coeff_low
            await ClockCycles(dut.clk, 1)

            dut.uio_in.value = LOAD_EN | IN_VALID | BYTE_EN
            dut.ui_in.value = coeff_high
            await ClockCycles(dut.clk,1)
        
        dut.uio_in.value = 0x00
        await ClockCycles(dut.clk,1)

async def load_sample(dut, sample):
    if (sample_width == 8):
        dut.uio_in.value = IN_VALID
        dut.ui_in.value = sample
        await ClockCycles(dut.clk, 1)
        dut.uio_in.value = 0x00
    elif (sample_width == 16):
        # double check make sure this mask works
        sample_low = sample & 0x00ff
        sample_high = (sample & 0xff00) >> 8

        dut.uio_in.value = IN_VALID
        dut.ui_in.value = sample_low
        await ClockCycles(dut.clk, 1)
        dut.uio_in.value = IN_VALID | BYTE_EN
        dut.ui_in.value = sample_high
        await ClockCycles(dut.clk, 1)
        dut.uio_in.value = 0x00

async def read_output(dut):
    if (sample_width == 8):
        out = dut.uo_out.value.to_signed()
        dut.uio_in.value = OUT_READY
        await ClockCycles(dut.clk,1)
        dut.uio_out.value = 0x00
        return out
    elif (sample_width == 16):
        out_low = dut.uo_out.value.to_unsigned()
        dut.uio_in.value = OUT_READY
        await ClockCycles(dut.clk,1)
        await Timer(1, units='ns')
        out_high = dut.uo_out.value.to_unsigned()
        dut.uio_in.value = OUT_READY
        await ClockCycles(dut.clk,1)
        dut.uio_in.value = 0x00
        result = ((out_high & 0xff) << 8) | (out_low & 0xff)

        if result & 0x8000:
            result -= 0x10000
        return result

@cocotb.test()
async def test_impulse_response(dut):
    clk = Clock(dut.clk, 10, "us")
    cocotb.start_soon(clk.start())

    h = firwin(taps, fc, fs=fs)
    cocotb.log.info(f"float coeffs = {h}")

    coeffs = h * normalize
    coeffs = [max(min_val, min(max_val, int(round(c)))) for c in coeffs]
    cocotb.log.info(f"fixed coeffs = {coeffs}")

    samples = [(2**(sample_width-1))-1,0,0,0,0,0,0,0]

    cocotb.log.info("----------------------------------")
    cocotb.log.info("           IMPULSE RESPONSE      ")
    cocotb.log.info("----------------------------------")

    await reset(dut)
    await load_coeff(dut, coeffs)

    for idx, s in enumerate(samples):

 

        # wait for in_ready
        while((dut.uio_out.value.to_unsigned() & IN_READY) == 0):
            await RisingEdge(dut.clk)

        # assert in_valid, load sample in
        await load_sample(dut, s)
        cocotb.log.info(f"sample {idx} = {s}")

        for i in range(taps):
            coeff = dut.tt_um_tpcannon7_fir.fir.coeff[i].value.to_signed()
            sample = dut.tt_um_tpcannon7_fir.fir.samples[i].value.to_signed()
            cocotb.log.info(f"coeff[{i}] = {coeff}, sample[{i}] = {sample}")   

        # wait for out_valid
        while((dut.uio_out.value.to_unsigned() & OUT_VALID) == 0):
            await RisingEdge(dut.clk)

        # TODO: straight truncation means off by 1, add rounding later
        # assert out_ready to accept sample
        res = await read_output(dut)
        cocotb.log.info(f"res = {res}")
        cocotb.log.info(f"expected = {coeffs[idx]}")
        assert abs(res - coeffs[idx]) <= 1, f"{res} does not match in acceptable range to {coeffs[idx]}"


@cocotb.test()
async def test_step_response(dut):
    clk = Clock(dut.clk, 10, "us")
    cocotb.start_soon(clk.start())

    # generate coeffs
    h = firwin(taps, fc, fs=fs)
    cocotb.log.info(f"float coeffs = {h}")
    
    # fixed point
    coeffs = h * normalize
    coeffs = [max(min_val, min(max_val, int(round(c)))) for c in coeffs]
    cocotb.log.info(f"fixed coeffs = {coeffs}")

    # step response
    samples = [0,0,0,0,0,0,0,0,(2**(sample_width-1))-1,(2**(sample_width-1))-1,(2**(sample_width-1))-1,
                (2**(sample_width-1))-1,(2**(sample_width-1))-1,(2**(sample_width-1))-1,
                (2**(sample_width-1))-1,(2**(sample_width-1))-1]

    cocotb.log.info("----------------------------------")
    cocotb.log.info("           STEP RESPONSE          ")
    cocotb.log.info("----------------------------------")

    await reset(dut)
    await load_coeff(dut, coeffs)

    out = 0

    for idx, s in enumerate(samples):
        # wait for in_ready
        while((dut.uio_out.value.to_unsigned() & IN_READY) == 0):
            await RisingEdge(dut.clk)

        # in_valid
        await load_sample(dut, s)
        cocotb.log.info(f"sample {idx} = {s}")

        # wait for out_valid
        while((dut.uio_out.value.to_unsigned() & OUT_VALID) == 0):
            await RisingEdge(dut.clk)

        # take sample out
        out = await read_output(dut)   

    expected = sum(coeffs)
    cocotb.log.info(f"out = {out}")
    cocotb.log.info(f"exp = {expected}")

    assert abs(out - expected) <= 1, f"{res} does not match within error to {expected}"
    
@cocotb.test()
async def test_noisy_sine(dut):
    clk = Clock(dut.clk, 10, "us")
    cocotb.start_soon(clk.start())

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

    y_fir = []
    samples = yraw * normalize
    samples = [max(min_val, min(max_val, int(round(s)))) for s in samples]

    # "true" filter
    samples_float = [s / float(normalize) for s in samples]
    y_lfilter = lfilter(h, 1.0, samples_float)

    await reset(dut)
    await load_coeff(dut, coeffs)

    cocotb.log.info("----------------------------------")
    cocotb.log.info("           NOISY SINE             ")
    cocotb.log.info("----------------------------------")


    for idx, s in enumerate(samples):
        while ((dut.uio_out.value.to_unsigned() & IN_READY) == 0):
            await ClockCycles(dut.clk, 1)

        # input sample
        await load_sample(dut, s)
        cocotb.log.info(f"sample {idx} = {s}")

        while ((dut.uio_out.value.to_unsigned() & OUT_VALID) == 0):
            await ClockCycles(dut.clk,1)

        out = await read_output(dut)
        out = out / float(normalize)
        y_fir.append(out)

    plt.plot(ts, yraw, 'k-')
    plt.plot(ts, y_lfilter, 'r-')
    plt.plot(ts, y_fir, 'c-')
    plt.legend(["raw","golden filter", "dut filter"])
    plt.savefig('output.png')

    gold_rms = math.sqrt(sum(x**2 for x in y_lfilter) / len(y_lfilter))
    dut_rms = math.sqrt(sum(x**2 for x in y_fir) / len(y_fir))
    err_rms = math.sqrt(sum((g - d)**2 for g, d in zip(y_lfilter, y_fir)) / len(y_fir))
    snr = 20.0 * math.log10(gold_rms / err_rms)

    assert snr > 30.0, f"SNR = {snr} below acceptable threshold"

    cocotb.log.info(f"SNR = {snr}")












