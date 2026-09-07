![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg) ![](../../workflows/fpga/badge.svg)

## D-FIR: SKY130 FIR Filter ASIC

- Submitted to the Tiny Tapeout SKY26c shuttle
- 36-tap, 12-bit fixed-point FIR filter
- Runtime coefficient reprogramming
  - Supports arbitrary coefficient sets, including symmetric (linear-phase) and asymmetric (non-linear-phase) FIR filters
- SPI Interface (Mode 0)
- 40 MHz internal clock
- ~294 kSps at 5 MHz SCLK
- **Design Documentation**
  - [General Operation](docs/info.md#general-operation)
  - [SPI Overview](docs/info.md#spi-overview)
  - [Truncated Baugh-Wooley Multiplier Design](docs/info.md#truncated-baugh-wooley-multiplier-design)
- **Pre-Silicon Validation**
  - ASIC RTL validated on a Gowin GW5A FPGA and STM32 Nucleo-F446RE
  - [FPGA Bring-up and Validation](bringup/README.md)
- **Cadence ASIC Implementation (GPDK045)**
  - [Cadence RTL-to-GDSII](asic/README.md)

## Architecture

```
             FIR_MODE (ui_in[0])
                  │
                  ▼
MOSI  ──┐     ┌───────────┐   rx_data  ┌──────────┐   din  ┌────────────┐
CS_N  ──┼────►│           ├───────────►│          ├───────►│            │
SCLK  ──┘     │    SPI    │            │ control  │        │ fir_filter │
              │           │◄───────────│          │◄───────│            │
MISO ◄────────┤           │   tx_data  └──────────┘  dout  └────────────┘
              └───────────┘
```

## Project Structure

- `src/`: Verilog design files
  - `tt_um_tpcannon7_fir.v`: Tiny Tapeout Top Level Wrapper
  - `fir_filter.v`: Core FIR datapath, samples/coefficient shift registers, instantiates truncated multiplier module
  - `trunc_mult.v`: Truncated Baugh-Wooley (Signed) 12x12 bit multiplier module
  - `spi.v`: SPI slave interface
  - `control.v`: Small control/routing layer to buffer SPI RX/TX and FIR core I/O
- `test/`: Cocotb testbenches
  - `fir_tb.py`: Verifies SPI functionality, impulse/step response, frequency response, and fixed-point output using SciPy reference models
  - `tb_trunc_mult/`: Truncated multiplier tests and cell/area statistics plot generation
- `docs/`: Project documentation
  - `info.md`: Main project datasheet for Tiny Tapeout
  - `CHANGELOG.md`: Project changelog
- `bringup/`: Pre-silicon validation using FPGA and STM32
  - `fpga/`: Gowin FPGA project, synthesis sources, constraints, and FPGA wrapper
  - `stm32/`: STM32CubeIDE firmware and Python interface used to communicate with the FPGA over SPI/UART
  - `README.md`: FPGA bring-up procedure, validation methodology, and hardware results

## GDS 2D Preview

![GDS 2D Preview](https://tpcannon7.github.io/ttsky-fir-tpcannon7/gds_render.png)

## Truncated Multiplier Area–Error Tradeoff

![Truncated Multiplier Tradeoff](docs/trunc_mult_tradeoff.png)

The 12×12 truncated multiplier (Baugh-Wooley signed, with Garofalo IC error correction) was synthesized against the Sky130A HD standard cell library across all DropBits parameters. The dashed line at DropBits=8 marks the design point used in the FIR filter.

## Pre-Silicon Validation Results
![Noisy Sine Filtering](docs/noisy_sine_fpga.png)

2 kHz sinusoid with added Gaussian noise, filtered with 3 kHz low pass coefficients. FPGA prototype output closely matches the floating-point SciPy reference.

![FPGA Error Plot](docs/error_fpga_plot.png)

Error remains bounded to approximately ±5 LSB relative to the floating-point reference, consistent with the fixed-point arithmetic and truncated multiplier design.

![FPGA/MCU Setup](docs/fpga_stm32_test_setup.png)

STM32 Nucleo-F446RE communicating with a Sipeed Tang Primer 25K FPGA over SPI. The FPGA runs the ASIC RTL @ 40 MHz while Python streams coefficients and samples over UART.

## Frequency Response

![Frequency Response](docs/impulse_freq_response.png)

50–60 kHz band-pass frequency response, computed from the measured impulse response vs. Python SciPy model
