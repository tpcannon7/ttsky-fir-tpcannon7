![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg) ![](../../workflows/fpga/badge.svg)

## D-FIR: A Tiny Tapeout FIR Filter

  - 12 bit samples/coefficients, 36 Taps
  - Runtime coefficient reprogramming
  - SPI Interface (Mode 0)
  - Internal clock @ 40 MHz
    - ~294 kSps @ SCLK = 5 MHz
  - SKY130 PDK
  - **See [info.md](docs/info.md) for more information**
    - [General Operation](docs/info.md#general-operation)
    - [SPI Overview](docs/info.md#spi-overview)
    - [Truncated Baugh-Wooley Multiplier Design](docs/info.md#truncated-baugh-wooley-multiplier-design)

## Project Structure

 - `src/`: Verilog design files directory
    - `tt_um_tpcannon7_fir.v`: Tiny Tapeout Top Level Wrapper
    - `fir_filter.v`: Core FIR logic, samples/coefficient shift lines, instantiates truncated multiplier module
    - `trunc_mult.v`: Truncated Baugh-Wooley (Signed) 12x12 bit multiplier module
    - `spi.v`: SPI slave interface
    - `control.v`: Small control/routing layer to buffer SPI RX/TX and FIR core I/O
 - `test/`: Cocotb testbenches
    - `fir_tb.py`: Cocotb python file containing FIR testbenches
      - Tests SPI interface, step/impulse response, filter comparison to Python scipy model etc.
 - `docs/`: Project documentation

## Pin Map

| Pin | Usage |
| --- |----   |
|`ui_in[0]`   | FIR_MODE pin for coefficient vs sample loading |
|`uio_in[0]`  |CS_N |
|`uio_in[1]`  |MOSI |
|`uio_out[2]` |MISO |
|`uio_in[3]`  | SCLK| 

## GDS 2D Preview

![GDS 2D Preview](https://tpcannon7.github.io/ttsky-fir-tpcannon7/gds_render.png)


## Truncated Multiplier Area–Error Tradeoff

![Truncated Multiplier Tradeoff](docs/trunc_mult_tradeoff.png)

The 12×12 truncated multiplier (Baugh-Wooley signed, with Garofalo IC error correction) was synthesized against the Sky130A HD standard cell library across all DropBits parameters. The dashed line at DropBits=8 marks the design point used in the FIR filter.

## Noisy Sinusoid Filtering Comparison

![Noisy Sine Filtering](docs/noisy_sine_comparison.png)

*2KHz sinusoid with added Gaussian noise, filtered with 10KHz low pass coefficients*

## Impulse Response

![Impulse Response](docs/impulse_response.png)

*10 KHz low pass filter impulse response*

## Step Response

![Step Response](docs/step_response.png)

## Frequency Response

![Frequency Response](docs/freq_response.png)

*50-60KHz band-pass frequency response*
