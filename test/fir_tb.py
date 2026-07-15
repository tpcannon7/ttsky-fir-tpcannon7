import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, Timer, ClockCycles, Combine, ValueChange
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
clock_period = 40 # 25mhz
# spi clock of 1-4mhz requires 2 NOP frames
# spi clock 5mhz < (not sure bounds) requires 4+ nop frames
spi_clock_period = 333 # ~3mhz
spi_frame_len = 16
nop_frames = 2

# params
taps = 28
data_width = 12

# max/min values for bit widths
min_val = -(2**(data_width-1))
max_val = (2**(data_width-1)-1)
normalize = ((2**(data_width-1)))

# Hz
fc = 10000
fc1 = 2000
fc2 = 5000
# extra spi clock period term to account for cs_n high between frames
total_spi_frame_time = (spi_clock_period * spi_frame_len) + spi_clock_period
fs = (1 / (total_spi_frame_time * 1e-9))

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
    dut.fir_mode.value = 1
    dut.spi_clock.value = 0
    dut.spi_cs_n.value = 1
    dut.spi_mosi.value = 1
    dut.ena.value = 1
    dut.rst_n.value = 0

    await ClockCycles(dut.clk, 50)

    dut.rst_n.value = 1

    await RisingEdge(dut.clk)

class SPIinterface:
    def __init__(self, spi_clock_period, dut):
        self.dut = dut
        self.spi_clock_period = spi_clock_period

        self.sclk = Clock(self.dut.spi_clock, self.spi_clock_period, "ns")

    async def transmit(self, data_in):
        data_in = (data_in & 0x0FFF) << 4 # double check
        rx_data = 0x0000
        self.dut.spi_cs_n.value = 0
        self.dut.spi_mosi.value = (data_in >> (spi_frame_len - 1)) & 0x0001
        await RisingEdge(self.dut.clk)
        cocotb.start_soon(self.sclk.start(start_high=False))
        for i in range(spi_frame_len):
            await RisingEdge(self.dut.spi_clock)
            out = int(self.dut.spi_miso.value)
            rx_data = (rx_data << 1) | out

            # shift mosi on falling edge
            await FallingEdge(self.dut.spi_clock)
            data_in = (data_in << 1) & 0xFFFF
            self.dut.spi_mosi.value = (data_in >> (spi_frame_len - 1)) & 0x0001
        
        self.sclk.stop()
        self.dut.spi_cs_n.value = 1
        await Timer(self.spi_clock_period, "ns")

        rx_data = (rx_data >> 4) & 0x0FFF

        if rx_data & 0x0800:
            rx_data -= 0x1000
        return rx_data

    async def load_coeff(self, coeffs):
        self.dut.fir_mode.value = 0
        await RisingEdge(self.dut.clk)
        # load in backwards due to coeff shift line
        for coeff in coeffs[::-1]:
            rx = await self.transmit(coeff)

        self.dut.fir_mode.value = 1

    async def load_samples(self, samples):
        rx = []
        self.dut.fir_mode.value = 1
        for idx, s in enumerate(samples):
            res = await self.transmit(s)
            await RisingEdge(self.dut.clk)
            rx.append(res)

        for _ in range(nop_frames):
            nop = await self.transmit(0x0000)
            rx.append(nop)

        return rx

@cocotb.test()
async def test_impulse_response(dut):
    clk = Clock(dut.clk, clock_period, "ns")
    cocotb.start_soon(clk.start())
    spi = SPIinterface(spi_clock_period, dut)

    h = firwin(taps, fc, fs=fs)
    coeffs = h * normalize
    coeffs = [max(min_val, min(max_val, int(round(c)))) for c in coeffs]
    cocotb.log.info(f"fixed coeffs = {coeffs}")

    samples = [max_val] + ([0] * (taps - 1))

    cocotb.log.info("----------------------------------")
    cocotb.log.info("         IMPULSE RESPONSE         ")
    cocotb.log.info("----------------------------------")

    await reset(dut)
    await spi.load_coeff(coeffs)

    # increasing spi clock leads to latency during FIR compute
    # 2 frame latency between input samples and output res on SPI MISO
    # samples N's result is available on sample N+2's tranmission
    outputs = await spi.load_samples(samples)
    cocotb.log.info(f"outputs (no trim) = {outputs}")
    # trim garbage frames
    outputs = outputs[nop_frames:]
    cocotb.log.info(f"outputs (trim leading garbage frames) = {outputs}")

    for idx, out in enumerate(outputs):
        assert abs(out - coeffs[idx]) <= 5, f"{out} does not match in acceptable range to {coeffs[idx]}"

@cocotb.test()
async def test_negative_impulse_response(dut):
    clk = Clock(dut.clk, clock_period, "ns")
    cocotb.start_soon(clk.start())
    spi = SPIinterface(spi_clock_period, dut)

    h = firwin(taps, fc, fs=fs)
    coeffs = h * normalize
    coeffs = [max(min_val, min(max_val, int(round(c)))) for c in coeffs]
    cocotb.log.info(f"fixed coeffs = {coeffs}")

    samples = [min_val] + ([0] * (taps - 1))

    cocotb.log.info("----------------------------------")
    cocotb.log.info("     NEGATIVE IMPULSE RESPONSE    ")
    cocotb.log.info("----------------------------------")

    await reset(dut)
    await spi.load_coeff(coeffs)

    # increasing spi clock leads to latency during FIR compute
    # 2 frame latency between input samples and output res on SPI MISO
    # samples N's result is available on sample N+2's tranmission
    outputs = await spi.load_samples(samples)
    cocotb.log.info(f"outputs (no trim) = {outputs}")
    # trim garbage frames
    outputs = outputs[nop_frames:]
    cocotb.log.info(f"outputs (trim leading garbage frames) = {outputs}")

    for idx, out in enumerate(outputs):
        assert abs(abs(out) - abs(coeffs[idx])) <= 5, f"{out} does not match in acceptable range to {coeffs[idx]}"

@cocotb.test()
async def test_step_response(dut):
    clk = Clock(dut.clk, clock_period, "ns")
    cocotb.start_soon(clk.start())
    spi = SPIinterface(spi_clock_period, dut)

    # generate coeffs
    h = firwin(taps, fc, fs=fs)
    # fixed point
    coeffs = h * normalize
    coeffs = [max(min_val, min(max_val, int(round(c)))) for c in coeffs]
    cocotb.log.info(f"fixed coeffs = {coeffs}")

    # step response
    samples = [0] * taps + [(2**(data_width-1))-1] * taps

    cocotb.log.info("----------------------------------")
    cocotb.log.info("           STEP RESPONSE          ")
    cocotb.log.info("----------------------------------")

    await reset(dut)
    await spi.load_coeff(coeffs)

    out = await spi.load_samples(samples)
    out = out[nop_frames:]

    expected = sum(coeffs)
    cocotb.log.info(f"out = {out}")
    cocotb.log.info(f"exp = {expected}")

    # across N taps we accumulate about error; for increasing # of taps we have more error due to serial MAC
    assert abs(out[-1] - expected) <= 30, f"{out} does not match within error to {expected}"
    
@cocotb.test()
async def test_noisy_sine(dut):
    clk = Clock(dut.clk, clock_period, "ns")
    cocotb.start_soon(clk.start())
    spi = SPIinterface(spi_clock_period, dut)

    cocotb.start_soon(cycle_counter(dut))

    # generate coeffs
    h = firwin(taps, fc, fs=fs)
    # fixed point
    coeffs = h * normalize
    coeffs = [max(min_val, min(max_val, int(round(c)))) for c in coeffs]
    cocotb.log.info(f"fixed coeffs = {coeffs}")

    # sine wave + noise (2 KHz)
    freq = 2000
    duration = 0.001
    n_samples = int(fs * duration)
    ts = np.linspace(0,duration,n_samples, endpoint=False)
    ys = np.sin(2*np.pi * freq * ts)
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
    await spi.load_coeff(coeffs)

    y_dut = await spi.load_samples(samples)
    y_dut = [v / float(normalize) for v in y_dut]

    # trim initial garbage spi frames (stale miso/filter not ready)
    y_dut = y_dut[nop_frames:]

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
    spi = SPIinterface(spi_clock_period, dut)

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
    await spi.load_coeff(coeffs)

    outputs = await spi.load_samples(samples)

    outputs = outputs[nop_frames:]

    cocotb.log.info(f"outputs = {outputs}")

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
    # fixed point
    coeffs = h * normalize
    coeffs = [max(min_val, min(max_val, int(round(c)))) for c in coeffs]
    coeffs = [c / float(normalize) for c in coeffs]

    w_dut, h_dut = freqz(coeffs, 1.0, fs=fs)
    w_true, h_true = freqz(h, 1.0, fs=fs)

    cocotb.log.info("----------------------------------")
    cocotb.log.info("         FREQUENCY RESPONSE       ")
    cocotb.log.info("----------------------------------")
    
    mag_dut = 20 * np.log10(np.maximum(abs(h_dut), 1e-6))
    mag_true = 20 * np.log10(np.maximum(abs(h_true), 1e-6))

    plt.title("Frequency Response of DUT vs. Python Model")
    plt.plot(w_dut, mag_dut, 'r-', label="dut frequency response")
    plt.plot(w_true, mag_true, 'c-', label="python model frequency response" )
    plt.axvline(fc, color='black', linestyle=':', linewidth=0.8, label="fc")
    plt.ylabel("Amplitude (dB)")
    plt.xlabel("Frequency (Hz)")
    plt.legend()
    plt.savefig('freq_response.png')

# test to verify new coeff shift reg works properly
@cocotb.test()
async def test_non_symmetric_coeff(dut):
    clk = Clock(dut.clk, clock_period, "ns")
    cocotb.start_soon(clk.start())
    spi = SPIinterface(spi_clock_period, dut)

    coeffs = [(i+1) / taps for i in range(taps)]
    coeffs = [c * normalize for c in coeffs]
    coeffs = [max(min_val, min(max_val, int(round(c)))) for c in coeffs]
    cocotb.log.info(f"fixed coeffs = {coeffs}")

    samples = [(2**(data_width-1))-1] + ([0] * (taps - 1))

    
    cocotb.log.info("----------------------------------")
    cocotb.log.info("    NON-SYMMETRIC COEFFCIENTS     ")
    cocotb.log.info("----------------------------------")

    await reset(dut)
    await spi.load_coeff(coeffs)

    outputs = await spi.load_samples(samples)

    outputs = outputs[nop_frames:]

    cocotb.log.info(f"outputs = {outputs}")
    cocotb.log.info(f"expected = {coeffs}")

    for idx, out in enumerate(outputs):
        assert abs(out- coeffs[idx]) <= 10, f"{out} != {coeffs[idx]}, order incorrect"


@cocotb.test()
async def test_load_coeffs_mid_sample_drive(dut):
    clk = Clock(dut.clk, clock_period, "ns")
    cocotb.start_soon(clk.start())
    sclk = Clock(dut.spi_clock, spi_clock_period, "ns")

    # impulse
    samples = [max_val] + [0] * (taps - 1)
    cocotb.log.info(f"samples = {samples}")

    h1 = firwin(taps,[fc1, fc2],pass_zero=False,fs=fs) # bandpass
    h2 = firwin(taps,fc,fs=fs) # low pass

    c1 = h1 * normalize
    c1 =[max(min_val,min(max_val,int(round(c)))) for c in c1]
    cocotb.log.info(f"c1 = {c1}")

    c2 = h2 * normalize
    c2 =[max(min_val,min(max_val,int(round(c)))) for c in c2]
    cocotb.log.info(f"c2 = {c2}")

    cocotb.log.info("----------------------------------")
    cocotb.log.info("    MID-SAMPLE DRIVE COEFF RELOAD ")
    cocotb.log.info("----------------------------------")

    await reset(dut)

    c1_outputs = []

    async def nop():
        outputs = []
        for _ in range(nop_frames):
            out = 0x0000
            nop = 0x0000
            dut.fir_mode.value = 1
            dut.spi_cs_n.value = 0
            await RisingEdge(dut.clk)
            cocotb.start_soon(sclk.start(start_high=False))
            dut.spi_mosi.value = (nop & 0x8000) >> spi_frame_len - 1
            for _ in range(spi_frame_len):
                await RisingEdge(dut.spi_clock)
                miso = int(dut.spi_miso.value)
                await FallingEdge(dut.spi_clock)
                out = (out << 1) | miso
                nop = nop << 1
                dut.spi_mosi.value = (nop & 0x8000) >> spi_frame_len - 1
            
            sclk.stop()
            dut.spi_cs_n.value = 1
            await Timer(spi_clock_period, "ns")

            out = out >> spi_frame_len - data_width

            if out & 0x0800:
                out -= 0x1000

            outputs.append(out)
        return outputs

    # load c1 coeffcients
    for idx, c in enumerate(c1):
        out = 0x0000
        c = (c & 0x0FFF) << spi_frame_len - data_width
        dut.fir_mode.value = 0
        dut.spi_cs_n.value = 0
        await RisingEdge(dut.clk)
        cocotb.start_soon(sclk.start(start_high=False))
        dut.spi_mosi.value = (c & 0x8000) >> (spi_frame_len - 1)
        for _ in range(spi_frame_len):
            await RisingEdge(dut.spi_clock)
            miso = int(dut.spi_miso.value)
            await FallingEdge(dut.spi_clock)
            c = (c << 1) & 0xFFFF
            out = (out << 1) | miso
            dut.spi_mosi.value = (c & 0x8000) >> (spi_frame_len - 1)

        
        sclk.stop()
        dut.spi_cs_n.value = 1
        await Timer(spi_clock_period, "ns")
        out = out >> spi_frame_len - data_width

        if out & 0x0800:
            out -= 0x1000

        c1_outputs.append(out)

    c1_outputs.append(await nop())


    pre_load_outputs = []
    post_load_outputs = []
    load_done = False

    cutoff_idx = taps // 2

    for idx, s in enumerate(samples):
        if (idx == cutoff_idx):
            for idx, c in enumerate(c2):
                c2_out = 0x0000
                c = (c & 0x0FFF) << spi_frame_len - data_width
                dut.fir_mode.value = 0
                dut.spi_cs_n.value = 0
                await RisingEdge(dut.clk)
                cocotb.start_soon(sclk.start(start_high=False))
                dut.spi_mosi.value = (c & 0x8000) >> spi_frame_len - 1
                for _ in range(spi_frame_len):
                    await RisingEdge(dut.spi_clock)
                    miso = int(dut.spi_miso.value)
                    await FallingEdge(dut.spi_clock)
                    c2_out = (c2_out << 1) | miso
                    c = (c << 1) & 0xFFFF
                    dut.spi_mosi.value = (c & 0x8000) >> spi_frame_len - 1

                sclk.stop()
                dut.spi_cs_n.value = 1
                await Timer(spi_clock_period, "ns")

                c2_out = c2_out >> spi_frame_len - data_width

                if c2_out & 0x0800:
                    c2_out -= 0x1000

                pre_load_outputs.append(c2_out)
            
            load_done = True
            nop_res = await nop()
            for n in nop_res: pre_load_outputs.append(n)

        s = (s & 0x0FFF) << spi_frame_len - data_width
        out = 0x0000
        dut.fir_mode.value = 1
        dut.spi_cs_n.value = 0
        await RisingEdge(dut.clk)
        cocotb.start_soon(sclk.start(start_high=False))
        dut.spi_mosi.value = (s & 0x8000) >> spi_frame_len - 1
        for _ in range(spi_frame_len):
            await RisingEdge(dut.spi_clock)
            miso = int(dut.spi_miso.value)
            await FallingEdge(dut.spi_clock)
            out = (out << 1) | miso
            s = (s << 1) & 0xFFFF
            dut.spi_mosi.value = (s & 0x8000) >> spi_frame_len - 1

        sclk.stop()
        dut.spi_cs_n.value = 1
        await Timer(spi_clock_period, "ns")

        out = out >> spi_frame_len - data_width
        if out & 0x0800:
            out -= 0x1000

        if load_done == True:
            post_load_outputs.append(out)
        else:
            pre_load_outputs.append(out)

    nop_res = await nop()
    for n in nop_res: post_load_outputs.append(n)

    cocotb.log.info(f"clipped c1 (taps/2 (top half)) = {c1[:(taps//2)]}")
    cocotb.log.info(f"clipped c2 (taps / 2 (bottom half)) = {c2[(taps//2):]}")
    
    # we miss c1's coeff #tap/2 because the result is flushed from the control layer
    # because of the previous load
    # coeff loading causing state machine to go from ready -> done instead of ready -> compute -> done
    # less cycles gives less time for previous result to be picked up by spi module; the quicker state machine 
    # turnaround on the coeff load overwrites the previous result before spi can pick it up into its tx buffer

    # cocotb.log.info(f"c1_outputs = {c1_outputs}")
    cocotb.log.info(f"pre_load_outputs = {pre_load_outputs}")
    cocotb.log.info(f"post_load_outputs = {post_load_outputs}")


@cocotb.test()
async def test_cs_n_assert_mid_sequence(dut):

    # choose random sample # to pull cs_n high during 
    # spi transcation
    rng = np.random.default_rng()
    rand_taps = rng.integers(0, high=taps, size=2)

    pass