![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg) ![](../../workflows/fpga/badge.svg)

## D-FIR: A Tiny Tapeout FIR Filter

  - 12 bit samples/coefficients, 36 Taps
  - Runtime coefficient reprogramming
    - Supports arbitrary coefficient sets, including symmetric (linear-phase) and asymmetric (non-linear-phase) FIR filters
  - SPI Interface (Mode 0)
  - Internal clock @ 40 MHz
    - *~294 kSps @ SCLK = 5 MHz*
  - SKY130 PDK
  - **Design Documentation**
    - [General Operation](docs/info.md#general-operation)
    - [SPI Overview](docs/info.md#spi-overview)
    - [Truncated Baugh-Wooley Multiplier Design](docs/info.md#truncated-baugh-wooley-multiplier-design)
  - **Hardware Validation**
    - Verified operation using Gowin GW5A FPGA and STM32 Nucleo-F446RE
    - FPGA validation uses the same RTL used for the ASIC implementation
    - [FPGA Bring-up and Validation](bringup/README.md)

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
 - `bringup/`: FPGA hardware validation
    - `fpga/`: Gowin FPGA project, synthesis sources, constraints, and FPGA wrapper
    - `stm32/`: STM32CubeIDE firmware and Python interface used to communicate with the FPGA over SPI/UART
    - `README.md`: FPGA bring-up procedure, validation methodology, and hardware results

## Pin Map

| Pin | Usage |
| --- |----   |
|`ui_in[0]`   | FIR_MODE (coefficients vs samples) |
|`uio_in[0]`  |CS_N |
|`uio_in[1]`  |MOSI |
|`uio_out[2]` |MISO |
|`uio_in[3]`  | SCLK| 

## GDS 2D Preview

![GDS 2D Preview](https://tpcannon7.github.io/ttsky-fir-tpcannon7/gds_render.png)

## Truncated Multiplier Area–Error Tradeoff

![Truncated Multiplier Tradeoff](docs/trunc_mult_tradeoff.png)

The 12×12 truncated multiplier (Baugh-Wooley signed, with Garofalo IC error correction) was synthesized against the Sky130A HD standard cell library across all DropBits parameters. The dashed line at DropBits=8 marks the design point used in the FIR filter.

## Hardware Validation: FPGA vs. Python Reference
![Noisy Sine Filtering](docs/noisy_sine_fpga.png)

2KHz sinusoid with added Gaussian noise, filtered with 3KHz low pass coefficients. FPGA output closely matches the floating-point SciPy reference.

## FPGA Error Plot
![FPGA Error Plot](docs/error_fpga_plot.png)

Error remains bounded to approximately ±5 LSB relative to the floating-point reference, consistent with the fixed-point arithmetic and truncated multiplier design.

## FPGA Hardware Validation Setup
![FPGA/MCU Setup](docs/fpga_stm32_test_setup.png)

STM32 Nucleo-F446RE communicating with a Sipeed Tang Primer 25K FPGA over SPI. The FPGA runs the ASIC RTL @ 40 MHz while Python streams coefficients and samples over UART.

## Frequency Response

![Frequency Response](docs/impulse_freq_response.png)

50-60KHz band-pass frequency response, computed from the measured impulse response vs. Python SciPy model
