# D-FIR Documentation

- **[info.md](info.md)** — Main project datasheet: general operation, SPI protocol, truncated multiplier design, and result plots
- **[CHANGELOG.md](CHANGELOG.md)** — Full project changelog

## Plots

| File | Description |
|------|-------------|
| `trunc_mult_tradeoff.png` | Area–error tradeoff sweep across DropBits (0–11) |
| `noisy_sine_fpga.png` | FPGA vs. Python lfilter on a noisy 2 kHz sinusoid |
| `noisy_sine_comparison.png` | RTL simulation: DUT vs. Python lfilter on a noisy 2 kHz sinusoid |
| `error_fpga_plot.png` | FPGA output error relative to floating-point SciPy reference |
| `impulse_response.png` | DUT impulse response vs. ideal fixed-point coefficients |
| `impulse_freq_response.png` | Frequency response reconstructed from measured impulse |
| `step_response.png` | DUT step response vs. Python lfilter |
| `fpga_stm32_test_setup.png` | FPGA + STM32 hardware validation setup |
