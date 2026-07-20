import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, Timer, ClockCycles, Combine, ValueChange
from cocotb.clock import Clock
from scipy.signal import firwin, lfilter, chirp, freqz
import numpy as np
import matplotlib.pyplot as plt
import math
import os

# clock period (ns)
clock_period = 25 # 40 MHz
# spi clock of 1-4mhz requires 2 NOP frames
# spi clock 5 MHz < (not sure bounds) requires 4+ nop frames
spi_clock_period = 200 # ~5 MHz
spi_frame_len = 16
nop_frames = 2

# params
taps = 36
data_width = 12

# max/min values for bit widths
min_val = -(2**(data_width-1))
max_val = (2**(data_width-1)-1)
normalize = ((2**(data_width-1)))

# Hz
fc = 10000
fc1 = 50000
fc2 = 60000
# extra spi clock period term to account for cs_n high between frames
total_spi_frame_time = (spi_clock_period * spi_frame_len) + spi_clock_period
fs = (1 / (total_spi_frame_time * 1e-9))

# random test seeding
TEST_SEED = int(os.getenv("FIR_TB_SEED", "12345"))

# bidirect pins
CS_N = 0x01
MOSI = 0x02
MISO = 0x04
SCLK = 0x08

MODE_COEFF = 0x0000
MODE_SAMPLE = 0x0001

async def reset(dut):
    dut.fir_mode.value = MODE_SAMPLE
    dut.spi_clock.value = 0
    dut.spi_cs_n.value = 1
    dut.spi_mosi.value = 1
    dut.ena.value = 1
    dut.rst_n.value = 0

    await ClockCycles(dut.clk, 50)

    dut.rst_n.value = 1

    await RisingEdge(dut.clk)

# spi interface wrapper
class SPIinterface:
    def __init__(self, spi_clock_period, dut, seed=TEST_SEED):
        self.dut = dut
        self.spi_clock_period = spi_clock_period
        self.sclk = Clock(self.dut.spi_clock, self.spi_clock_period, "ns")
        self.rng = np.random.default_rng(seed)

    async def _transmit(self, data_in):
        data_in = (data_in & 0x0FFF) << 4
        rx_data = 0x0000
        self.dut.spi_cs_n.value = 0
        self.dut.spi_mosi.value = (data_in >> (spi_frame_len - 1)) & 0x0001
        await RisingEdge(self.dut.clk)
        cocotb.start_soon(self.sclk.start(start_high=False))
        for i in range(spi_frame_len):
            await RisingEdge(self.dut.spi_clock)
            out = int(self.dut.spi_miso.value)
            rx_data = (rx_data << 1) | out
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

    async def transfer(self, data, mode, reverse=False, append_nop=0):
        self.dut.fir_mode.value = mode
        await RisingEdge(self.dut.clk)

        if reverse:
            data = data[::-1]

        rx = []
        for d in data:
            rx.append(await self._transmit(d))
            if mode == 1:
                await RisingEdge(self.dut.clk)

        for _ in range(append_nop):
            rx.append(await self._transmit(0x0000))

        return rx

    async def transfer_bad(self, data, mode, fault_rate, reverse=False):
        rx = []

        if reverse:
            data = data[::-1]

        idx = 0
        while idx < len(data):
            d = data[idx]
            out = 0x0000
            s = (d & 0x0FFF) << (spi_frame_len - data_width)

            self.dut.fir_mode.value = mode
            self.dut.spi_cs_n.value = 0
            await RisingEdge(self.dut.clk)
            cocotb.start_soon(self.sclk.start(start_high=False))
            self.dut.spi_mosi.value = (s & 0x8000) >> (spi_frame_len - 1)

            cs_high_flag = self.rng.random() < fault_rate
            cs_high_bit = self.rng.integers(low=1, high=spi_frame_len - 1)
            bad_transact = False

            for bit_idx in range(spi_frame_len):
                if cs_high_flag and bit_idx == cs_high_bit:
                    label = "coeff" if mode == 0 else "samples"
                    cocotb.log.info(f"CS_N HIGH @ bit {bit_idx} of {label} {idx} = {data[idx]}")
                    self.dut.spi_cs_n.value = 1
                    self.sclk.stop()
                    await Timer(self.spi_clock_period, "ns")
                    bad_transact = True
                    break

                await RisingEdge(self.dut.spi_clock)
                miso = int(self.dut.spi_miso.value)
                await FallingEdge(self.dut.spi_clock)
                s = (s << 1) & 0xFFFF
                out = (out << 1) | miso
                self.dut.spi_mosi.value = (s & 0x8000) >> (spi_frame_len - 1)

            if bad_transact:
                continue

            self.sclk.stop()
            self.dut.spi_cs_n.value = 1
            await Timer(self.spi_clock_period, "ns")

            out = out >> (spi_frame_len - data_width)
            if out & 0x0800:
                out -= 0x1000
            rx.append(out)
            idx += 1

        return rx

    async def load_coeff(self, coeffs):
        result = await self.transfer(coeffs, mode=MODE_COEFF, reverse=True)
        self.dut.fir_mode.value = MODE_SAMPLE
        return result

    async def load_samples(self, samples, nop=nop_frames):
        return await self.transfer(samples, mode=MODE_SAMPLE, reverse=False, append_nop=nop)

    async def load_coeff_random_bad_transact(self, coeffs, percent):
        return await self.transfer_bad(coeffs, mode=MODE_COEFF, fault_rate=percent, reverse=True)

    async def load_samples_random_bad_transact(self, samples, percent):
        return await self.transfer_bad(samples, mode=MODE_SAMPLE, fault_rate=percent, reverse=False)

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
    # samples N's result is available on sample N+2's transmission
    outputs = await spi.load_samples(samples)
    cocotb.log.info(f"outputs (no trim) = {outputs}")
    # trim garbage frames
    outputs = outputs[nop_frames:]
    cocotb.log.info(f"outputs (trim leading garbage frames) = {outputs}")

    samples_float = [s / float(normalize) for s in samples]
    y_lfilter = lfilter(h, 1.0, samples_float)
    y_lfilter_int = y_lfilter * normalize
    y_lfilter_int = [max(min_val, min(max_val, int(round(v)))) for v in y_lfilter_int]

    cocotb.log.info(f"python lfilter = {y_lfilter_int}")

    for idx, out in enumerate(outputs):
        assert abs(out - y_lfilter_int[idx]) <= 3, f"{out} does not match in acceptable range to {y_lfilter_int[idx]}"

    plt.figure()
    plt.plot(y_lfilter_int, 'b.--', label='python lfilter', linewidth=1.5)
    plt.plot(outputs, 'r-', label='DUT output', linewidth=1)
    plt.ylabel("Amplitude (Integer Steps)")
    plt.xlabel("Sample Count")
    plt.title("Impulse Response: DUT vs. Python Model")
    plt.legend()

    try:
        plt.savefig('impulse_response.png')
    except OSError as e:
        cocotb.log.warning(f"Failed to save impulse_response plot: {e}")

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

    outputs = await spi.load_samples(samples)
    outputs = outputs[nop_frames:]

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
    coeffs_float = [c / float(normalize) for c in coeffs]
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

    # python model
    samples_float = [s / float(normalize) for s in samples]
    y_lfilter = lfilter(h, 1.0, samples_float)
    y_lfilter_int = [max(min_val, min(max_val, int(round(v * normalize)))) for v in y_lfilter]

    expected = sum(coeffs)
    cocotb.log.info(f"out = {out}")
    cocotb.log.info(f"exp = {expected}")

    for idx, v in enumerate(out):
        assert abs(out[idx] - y_lfilter_int[idx]) <= 30, \
            f"Step mismatch at sample {idx}: DUT={out[idx]} python={y_lfilter_int[idx]}"

    plt.figure()
    plt.plot(y_lfilter_int, 'b.--', label='python lfilter', linewidth=1.5)
    plt.plot(out, 'r-', label='DUT', linewidth=1)
    plt.ylabel("Amplitude (Integer Steps)")
    plt.xlabel("Sample Count")
    plt.title("Step Response: DUT vs. Python Model")
    plt.legend()

    try:
        plt.savefig('step_response.png')
    except OSError as e:
        cocotb.log.warning(f"Failed to save step_response plot: {e}")
    
@cocotb.test()
async def test_noisy_sine(dut):
    clk = Clock(dut.clk, clock_period, "ns")
    cocotb.start_soon(clk.start())
    spi = SPIinterface(spi_clock_period, dut)

    rng = np.random.default_rng(TEST_SEED)

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
    yerr = 0.5 * rng.normal(size=len(ts))
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

    plt.figure()
    plt.plot(ts, yraw, 'k-', linewidth=0.5, label='raw')
    plt.plot(ts, y_lfilter, 'b--', label='python lfilter', linewidth=1.5)
    plt.plot(ts, y_dut, 'r-', label='DUT', linewidth=1)
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.title("Noisy Sinusoid Filtering: DUT vs. Python model")
    plt.legend()

    try:
        plt.savefig('noisy_sine_comparison.png')
    except OSError as e:
        cocotb.log.warning(f"Failed to save noisy_sine plot: {e}")

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

# not a real test; generates freq response plots vs python model
@cocotb.test()
async def test_frequency_response(dut):
    clk = Clock(dut.clk, clock_period, "ns")
    cocotb.start_soon(clk.start())

    await reset(dut)

    # generate coeffs
    h = firwin(taps, [fc1, fc2], pass_zero=False, fs=fs)
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
    phase_dut = np.angle(h_dut)
    phase_true = np.angle(h_true)

    plt.subplot(2, 1, 1)
    plt.title("Frequency Response of 12-bit fixed point vs. Python Model")
    plt.plot(w_dut, mag_dut, 'r-', label="12-bit fixed-point", linewidth=1)
    plt.plot(w_true, mag_true, 'b--', label="python model", linewidth=1.5)
    plt.ylabel("Magnitude (dB)")
    plt.legend()

    plt.subplot(2, 1, 2)
    plt.plot(w_dut, phase_dut, 'r-', label="12-bit fixed-point", linewidth=1)
    plt.plot(w_true, phase_true, 'b--', label="python model", linewidth=1.5)

    plt.ylabel("Phase (rad)")
    plt.xlabel("Frequency (Hz)")
    plt.legend()
    plt.tight_layout()
    try:
        plt.savefig('freq_response.png')
    except OSError as e:
        cocotb.log.warning(f"Failed to save freq_response plot: {e}")

# verify that coefficient shift reg behavior works as expected (coefficients must be loaded in reverse order where final tap goes first etc.)
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
    cocotb.log.info("    NON-SYMMETRIC COEFFICIENTS    ")
    cocotb.log.info("----------------------------------")

    await reset(dut)
    await spi.load_coeff(coeffs)

    outputs = await spi.load_samples(samples)

    outputs = outputs[nop_frames:]

    cocotb.log.info(f"outputs = {outputs}")
    cocotb.log.info(f"expected = {coeffs}")

    for idx, out in enumerate(outputs):
        assert abs(out- coeffs[idx]) <= 10, f"{out} != {coeffs[idx]}, order incorrect"

# not a real test no assertions
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
            dut.fir_mode.value = MODE_SAMPLE
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

    # load c1 coefficients
    for idx, c in enumerate(c1):
        out = 0x0000
        c = (c & 0x0FFF) << spi_frame_len - data_width
        dut.fir_mode.value = MODE_COEFF
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


    pre_load_outputs = []
    post_load_outputs = []
    load_done = False

    cutoff_idx = taps // 2

    for idx, s in enumerate(samples):
        if (idx == cutoff_idx):
            for idx, c in enumerate(c2):
                c2_out = 0x0000
                c = (c & 0x0FFF) << spi_frame_len - data_width
                dut.fir_mode.value = MODE_COEFF
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
        dut.fir_mode.value = MODE_SAMPLE
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
async def test_cs_n_assert_mid_frame(dut):
    clk = Clock(dut.clk, clock_period, "ns")
    cocotb.start_soon(clk.start())
    spi = SPIinterface(spi_clock_period, dut)

    h = firwin(taps, fc, fs=fs)
    coeffs = h * normalize
    coeffs = [max(min_val,min(max_val,int(round(c)))) for c in coeffs]

    samples = [max_val] + [0] * (taps - 1)
    nop = [0x0000] * nop_frames

    cocotb.log.info("----------------------------------")
    cocotb.log.info("        CS_N HIGH MID FRAME       ")
    cocotb.log.info("----------------------------------")

    await reset(dut)

    cs_n_fault_rate = 0.50

    coeffs_outputs = await spi.load_coeff_random_bad_transact(coeffs, cs_n_fault_rate)

    samples_out = await spi.load_samples_random_bad_transact(samples, cs_n_fault_rate)
    nop_out = await spi.load_samples_random_bad_transact(nop, cs_n_fault_rate)
    for n in nop_out: samples_out.append(n)

    cocotb.log.info(f"samples_out no nop trim = {samples_out}")

    samples_out = samples_out[nop_frames:]

    cocotb.log.info(f"coeffs = {coeffs}")
    # cocotb.log.info(f"coeffs out = {coeffs_outputs}")
    cocotb.log.info(f"samples_out = {samples_out}")

    for idx,o in enumerate(samples_out):
        assert abs(o - coeffs[idx]) <= 5, f"erroneous cs_n fault coeff mismatch with {o} vs expected={coeffs[idx]}"

@cocotb.test()
async def test_coeff_reload(dut):
    clk = Clock(dut.clk, clock_period, "ns")
    cocotb.start_soon(clk.start())
    
    sclk = Clock(dut.spi_clock, spi_clock_period, "ns")
    
    spi = SPIinterface(spi_clock_period, dut)

    h = firwin(taps, fc, fs=fs)
    coeffs = h * normalize
    coeffs = [max(min_val,min(max_val,int(round(c)))) for c in coeffs]

    h_other = firwin(taps, [fc1,fc2], pass_zero=False, fs=fs)
    coeffs_other = h_other * normalize
    coeffs_other = [max(min_val,min(max_val,int(round(c)))) for c in coeffs_other]

    impulse = [max_val] + [0] * (taps-1)

    
    cocotb.log.info("----------------------------------")
    cocotb.log.info("    COEFF RELOAD WITH IMPULSE     ")
    cocotb.log.info("----------------------------------")

    await reset(dut)
    c_out = await spi.load_coeff(coeffs)

    c1_out_impulse = await spi.load_samples(impulse)
    c1_out_impulse_trim = c1_out_impulse[nop_frames:]

    cocotb.log.info(f"expected coeffs = {coeffs}")
    cocotb.log.info(f"first impulse out = {c1_out_impulse_trim}")

    for idx, o in enumerate(c1_out_impulse_trim):
        assert abs(o - coeffs[idx]) <= 5, f"impulse response {o} does not match {coeffs[idx]}"

    # load other coefficients
    c_other_out = await spi.load_coeff(coeffs_other)
    c_other_impulse = await spi.load_samples(impulse)
    c_other_impulse_trim = c_other_impulse[nop_frames:]

    cocotb.log.info(f"expected new reload coeffs = {coeffs_other}")
    cocotb.log.info(f"reload coefficients impulse = {c_other_impulse_trim}")

    for idx, o in enumerate(c_other_impulse_trim):
        assert abs(o - coeffs_other[idx]) <= 5, f"impulse response {o} does not match {coeffs_other[idx]}"

@cocotb.test()
async def test_overflow(dut):
    clk = Clock(dut.clk, clock_period, "ns")
    cocotb.start_soon(clk.start())
    spi = SPIinterface(spi_clock_period, dut)

    coeffs = [max_val] * taps
    samples = [max_val] * (taps * 2)

    cocotb.log.info("----------------------------------")
    cocotb.log.info("          OVERFLOW TEST           ")
    cocotb.log.info("----------------------------------")

    await reset(dut)
    await spi.load_coeff(coeffs)
    
    outputs = await spi.load_samples(samples)
    outputs = outputs[nop_frames:]

    cocotb.log.info(f"outputs = {outputs}")
    prev_sample = 0
    for n in outputs:
        assert n >= prev_sample, f"{n} should be greater equal to prev sample={prev_sample}"
        prev_sample = n
    
    assert outputs[-1] == max_val, f"{outputs[-1]} is not the saturated max_val of {max_val}"

    
