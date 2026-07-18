![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg) ![](../../workflows/fpga/badge.svg)

## D-FIR: A Tiny Tapeout FIR Filter

  - 12 bit samples/coeffcients, 28 Taps
  - Runtime coeffcient reprogramming
  - SPI Interface (Mode 0)
  - Internal clock @ 25 MHz
  - SKY130 PDK
  - **See [info.md](docs/info.md) for more information relating to architecture and general operation**

## Project Structure

 - `src/`: Verilog design files directory
    - `tt_um_tpcannon7.v`: Tiny Tapeout Top Level Wrapper
    - `fir_filter.v`: Core FIR logic, samples/coeffcient shift lines, truncated multiplier module
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
|`ui_in[0]`   | MODE pin for coeffcient vs sample loading |
|`uio_in[0]`  |CS_N |
|`uio_in[1]`  |MOSI |
|`uio_out[2]` |MISO |
|`uio_in[3]`  | SCLK| 

## Impulse Response

![Impulse Response](docs/impulse_response.png)

## Step Response

![Step Response](docs/step_response.png)

## Noisy Sinusoid Filtering Comparison

![Noisy Sine Filtering](docs/noisy_sine_comparison.png)

- 2KHz sinusoid with added Gaussian noise, filtered with 10KHz low pass coeffcients

## Frequency Response

![Frequency Response](docs/freq_response.png)

- 50-60KHz band-pass