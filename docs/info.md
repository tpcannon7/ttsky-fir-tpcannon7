<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## SPI Overview

  - 16 bit frames; leading MSB, remaining lower bits padded with 0's
  - SPI Mode 0 only
  - SCLK speed up to 3-4MHz
  - Depending on chosen SCLK speed may require different number of don't care leading SPI frames + trailing NOP frames to drain all FIR results
      - First few frames of SPI will contain garbage data (0's) before results are shown
      - Ater the final sample is input, N number of NOP frames (0x0000) samples are required to be sent to drain final result

## How it works

 - Load samples or coeffcients over SPI interface
    - Use MODE ui_in[0] pin to switch between coeffcient or sample loading
    - MODE 0 (LOW): Coeffcients; MODE 1 (HIGH): Samples
    - Coeffcients are in format Q1.11, 11 decimal bits
        - When generating coeffcient vector, ensure you multiply by $2^{11}$ and round to the nearest whole number to match the expected input shape

## How to test

- Recommended to generate own array of filter coeffcients using Python or other online tools
- Load coeffcients over SPI
- Send impulse response and verify outputs match with loaded filter coeffcients

## External hardware

- SPI Pmod (optional?)
