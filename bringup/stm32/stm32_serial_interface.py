import serial
import logging
import math

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import firwin, lfilter

# make sure WSL can see usb debugger of stm32
# usbipd list
# usbipd attach --wsl --busid <bus-id>

taps = 36
fc = 3000
fc1 = 2000
fc2 = 5000
spi_freq = 2625000
spi_frame_len = 16
fs = 102500

data_width = 12
min_val = -(2 ** (data_width - 1))
max_val = (2 ** (data_width - 1) - 1)
normalize = (2 ** (data_width - 1))

# UART bytes
block_size = 256
# SPI samples
spi_block_size = 128
# FPGA pipeline latency
nop_frames = 1

logging.basicConfig(
    format="%(levelname)s:%(name)s:%(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


def main():
    rng = np.random.default_rng(seed=12345)

    # FIR coefficients
    h = firwin(taps, fc, fs=fs)
    coeffs = np.round(h * normalize).astype(np.int16)
    coeffs = np.clip(coeffs, min_val, max_val)
    logger.info(f"coeffs={coeffs}")

    coeff_block = np.zeros(spi_block_size, dtype=np.int16)
    coeff_block[-taps:] = coeffs << 4

    # Noisy sine
    freq = 2000
    duration = 0.003
    n_samples = int(fs * duration)
    ts = np.arange(n_samples) / fs
    ys = np.sin(2 * np.pi * freq * ts)
    noise = 0.5 * rng.normal(size=n_samples)
    yraw = ys + noise

    samples = np.round(yraw * normalize).astype(np.int16)
    samples = np.clip(samples, min_val, max_val)

    # Golden model
    samples_float = samples.astype(np.float64) / normalize
    y_lfilter = lfilter(h, 1.0, samples_float)

    # Flush block
    nop = np.zeros(spi_block_size, dtype=np.int16)

    # FPGA output
    y_fpga = []

    with serial.Serial("/dev/ttyACM0", 921600, timeout=5) as ser:
        logger.info("UART Open")

        # Load coefficients
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        ser.write(coeff_block.tobytes())
        coeff_out = np.frombuffer(ser.read(block_size),dtype=np.int16).copy()

        # Stream sample blocks
        for start in range(0, n_samples, spi_block_size):
            block = np.zeros(spi_block_size, dtype=np.int16)
            chunk = samples[start:start + spi_block_size]
            block[:len(chunk)] = chunk << 4

            ser.reset_input_buffer()
            ser.reset_output_buffer()
            ser.write(block.tobytes())

            rx = np.frombuffer(ser.read(block_size),dtype=np.int16).copy()
            rx = np.right_shift(rx, 4)

            logger.info(f"rx={rx[:20]}")
            y_fpga.extend(rx)


        # Flush remaining pipeline samples
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        ser.write(nop.tobytes())
        nop_out = np.frombuffer(ser.read(block_size),dtype=np.int16).copy()

        nop_out = np.right_shift(nop_out, 4)
        # Only keep the valid pipeline outputs
        y_fpga.extend(nop_out[:nop_frames])

    # Convert to float
    y_fpga = np.asarray(y_fpga, dtype=np.int16)
    # Remove initial latency
    y_fpga = y_fpga[nop_frames:]
    # Match original signal length
    y_fpga = y_fpga[:n_samples]
    y_fpga = y_fpga.astype(np.float64) / normalize

    # Keep reference same length
    y_lfilter[nop_frames:]
    y_lfilter = y_lfilter[:len(y_fpga)]
    ts = ts[:len(y_fpga)]
    yraw = yraw[:len(y_fpga)]

    # Metrics
    gold_rms = math.sqrt(np.mean(y_lfilter ** 2))
    dut_rms = math.sqrt(np.mean(y_fpga ** 2))
    err_rms = math.sqrt(np.mean((y_lfilter - y_fpga) ** 2))
    snr = 20.0 * math.log10(gold_rms / err_rms)

    logger.info(f"DUT RMS = {dut_rms}")
    logger.info(f"SNR = {snr:.2f} dB")

    # Plot
    fig = plt.figure()
    plt.plot(ts, yraw, "k-", linewidth=0.5, label="Raw")
    plt.plot(ts, y_lfilter, "b--", linewidth=1.5, label="Python")
    plt.plot(ts, y_fpga, "r-", linewidth=1.0, label="FPGA")
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.title("Noisy Sinusoid Filtering: FPGA vs. Python lfilter Model")
    plt.legend()
    plt.savefig("noisy_sine_fpga.png")
    plt.close(fig)

    error = (y_fpga - y_lfilter) * normalize

    idx = np.argmax(np.abs(error))

    print("index:", idx)
    print("error:", error[idx])

    for i in range(idx-3, idx+4):
        print(i, yraw[i], y_lfilter[i], y_fpga[i])

    fig = plt.figure()
    plt.plot(ts, error, "k-", label="Error")
    plt.title("FPGA error vs. Python lfilter model")
    plt.xlabel("Time (s)")
    plt.ylabel("Error")
    plt.legend()
    plt.savefig("error_fpga_plot.png")
    plt.close(fig)

    err0 = np.sqrt(np.mean((y_fpga - y_lfilter)**2))

    # FPGA delayed by 1 sample
    err1 = np.sqrt(np.mean((y_fpga[:-1] - y_lfilter[1:])**2))

    # FPGA advanced by 1 sample
    errm1 = np.sqrt(np.mean((y_fpga[1:] - y_lfilter[:-1])**2))

    print(err0, err1, errm1)


if __name__ == "__main__":
    main()
