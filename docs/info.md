<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## General Operation

 - Load samples or coeffcients over SPI interface
    - Use MODE ui_in[0] pin to switch between coeffcient or sample loading
    - MODE 0 (LOW): Coeffcients; MODE 1 (HIGH): Samples
    - Coeffcients are in format Q1.11, 11 decimal bits
        - When generating coeffcient vector, ensure you multiply by $2^{11}$ and round to the nearest whole number to match the expected input shape/width
    - Coeffcients must be loaded in **reverse order** (last tap first) due to the coefficient shift register architecture
    - There is an expected amount of error due to the fixed point representation and truncated multiplier precision
        - Truncated multiplier accumulates error with across taps due to serial MAC archiecture (one multiplier is used across all taps)
    - **Recommended first test:**
        - Generate own array of filter coeffcients using Python or other online tools (ex. Python scipy firwin function)
        - Load coeffcients over SPI
        - Send impulse response (impulse is equal to 2047 which is max positive value at 12 bit signed)
        - Verify outputs match with within an acceptable range to loaded filter coeffcients (acceptable range is around 1-2 integer steps, you may load a coeffcient of -5 but receive back an output of -6)

## SPI Overview

  - 16 bit frames; leading MSB, remaining lower bits padded with 0's
  - SPI Mode 0 only
  - SCLK speed up to 3-4MHz
  - Depending on chosen SCLK speed may require different number of don't care leading SPI frames + trailing NOP frames to drain all FIR results
      - First few frames of SPI will contain garbage data (0's) before results are shown
      - After the final sample is input, N number of NOP frames (0x0000) samples are required to be sent to drain final result
  - NOP frames needed depend on FIR compute pipeline depth:
      - At 3MHz SCLK: 2 trailing NOP frames
      - At higher SCLK speeds, more NOP frames may be required
      - NOPs are dummy SPI transactions that shift out the last FIR result from the MISO shift register

## SPI Timing

Loading Samples: 
```
MODE _/¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯\_
CS_N  \__________________________________________________________________________________/
SCLK  _/¯\_/¯\_/¯\_/¯\_/¯\_/¯\_/¯\_/¯\_/¯\_/¯\_/¯\_/¯\_/¯\_/¯\_/¯\_/¯\/¯\_/¯\_/¯\_/¯\_/¯\_
MOSI  X  b15  b14  b13  b12  b11  b10  b9   b8   b7   b6   b5   b4   b3   b2   b1   b0  X
MISO  X  d15  d14  d13  d12  d11  d10  d9   d8   d7   d6   d5   d4   d3   d2   d1   d0  X
```

Loading Coeffcients:
```
MODE \___________________________________________________________________________________/
CS_N  \__________________________________________________________________________________/
SCLK  _/¯\_/¯\_/¯\_/¯\_/¯\_/¯\_/¯\_/¯\_/¯\_/¯\_/¯\_/¯\_/¯\_/¯\_/¯\_/¯\/¯\_/¯\_/¯\_/¯\_/¯\_
MOSI  X  b15  b14  b13  b12  b11  b10  b9   b8   b7   b6   b5   b4   b3   b2   b1   b0  X
MISO  X  d15  d14  d13  d12  d11  d10  d9   d8   d7   d6   d5   d4   d3   d2   d1   d0  X
```

- 16 clock cycles per frame
- MOSI driven on SCLK falling edge, MISO sampled on SCLK rising edge (SPI Mode 0)
- MODE pin (ui_in[0]) is sampled at bit 8 (mid-frame) to determine coefficient vs sample loading
- Data is 12-bit, MSB leading, right-padded with 4 lower zero bits to fill the 16-bit frame

## Truncated Baugh-Wooley Multiplier Design
*Note: this was from prior 16x16 design, same logic applies to current 12x12 multiplier, instead of dropping full fractional bits we only drop 8 to preserve performance vs. area; same algortihm for error correction applies as well with drop bits = 8.*

- 16x16 bit multiplier, truncating (dropping) the bottom 15 bits [14:0]
- Uses the Baugh-Wooley aglorithm to handle signed multiplication
    - "A Two's Complement Parallel Array Multiplication Algorithm" Baugh and Wooley
- Uses error correction scheme with IC terms to handle error stemming from truncation
    - "Low Error Truncated Multipliers for DSP Applications" Garafolo et al.
    - Optimized for lowest mean square error along with area

### Overview
- **Truncated multiplier to minimize area**
    - We use truncation specifically due to the fixed point of the coeffcient terms in the FIR filter math
    - In the original design, we would compute all 32 product bits stemming from the 16x16 mutliplciation but drop the bottom 15 bits due to using Q1.15 fixed point format for the coeffcients
    - The idea is that since we never use these bits in our final integer output, we can avoid computing them at all which saves hardware area
    - The approach taken in this case was to first create a bit vector of all partial products per column, largest possible width is 16 partial products in a column in our case
    - We place each partial products AND result into its respective bit postion in the vector for the next step of summation
    - The partial product vectors for each column are then collapsed/summed into a smaller vector to count the contribution of each column to the final total product
    - Finally, we accumulate across each summed product columns, **making sure to account for the weight of each column** (ex. we shift left 16 bits for partial product column 16 to align with the correct bit position and preserve weighting)
- **Baugh-Wooley Algorithm** ("A Two's Complement Parallel Array Multiplication Algorithm" Baugh and Wooley)
    - An issue with the truncation method is that it does not natively handle signed (2's complement) multiplication
    - This is fixed by using the Baugh-Wooley algorithm which inverts certain terms in partial products along with the addition of new terms in partial product columns
        - Every y and x term less than (y~i~ < y~m-1~) and (x~i~ < x~n-1~) is inverted in their respective partial product pairs
        - Special case for y~i~ = y~m-1~ and x~i~ = x~n-1~ where this partial product pair is left unchanged (no inversion)
        - Extra terms added
            - Inverted single terms of y~m-1~ and x~n-1~ are added to the OutputWidth - 2 (16x16 = 32 bit -> Column/bit 30) partial product column 
            - Single bit "1" added to the final partial product column, OutputWidth - 1 (Column/bit 31)
            - Two single y~m-1~ and x~n-1~ terms are add at P~m-1~ and P~n-1~ respectively, special case when m = n (both operands are equal bit width) where terms are added to the same partial product column
- **IC Error Correction** ("Low Error Truncated Multipliers for DSP Applications" Garafolo et al.)
    - Truncation invovles some intrinsic error due to lost partial product terms and carry out from dropped partial product columns
    - We can recover some accuracy by implemneting an error correction scheme
    - Since we drop the bottom 15 bits [14:0], and our bit width for our inputs equals to 16, we compute our "h" term to be input bit width - dropped bits = 1.
        - "h" represents the number of extra bits kept beyond the minimum necessary of n = 16 bits (matching our input bit width)
    - In order to implement the error compensation, we must calculate the partial products in the one column below our first non-dropped column
        - In our case, drop bits = 15, in our truncated multiplier we compute partial products for columns [31:15]. We must now compute one column lower at column 14 ([drop bits = 15] drop  bits - 1 = 15 - 1 = 14)
        - Once this extra lower column has their partial products computed, we must apply the correct f(IC) function on specific bits (Eq. 20, pg. 31)
        - For partial products i = 1, 2, n-h-1 (16 - 1 - 1 = 14), n-h (16-1 = 15) we will sum them together and shift them all by $2^{-n-h-1}$ where -n-h-1 = -16-1-1 = -18
            - *These are our "edge IC terms"*
        - For partial products 2 < i < n-h-1, we apply the shift of $2^{-n-h}$ or $2*2^{-n-h-1}$ to them, with our K term coming to be 0
            - *"These are our "middle IC terms"*
        - The term shift can be confusing in this context espcially with using negative power of 2 terms
            - The paper uses reverse style for MSB and LSB where the MSB (or most significant product) is at $2^-1$ place and the LSB (least significant product) is at the $2^-{2n}$ place
            - Since our output with with 16x16 multiplication is 32 bits and we truncate the bottom 15 bits for our output, we must align these at 18 and 17 bits from the left respectively
            - This comes out to 32 - 18 = 14 and 32 - 17 = 15. These fit into partial product column 14 and 15 respectively
        - We must align the edge IC sum partial products and the middle IC sum partial products to their respective bit postions and add them to the main accumulation term
        - One thing to notice is that we do not have a bit 14 in our output of [31:15]. We must expand our accumulator term by one bit width, align the edge IC term with that lower bit and then add normally
        - The middle IC terms align to bit 15, so since we add that lower bit to account for the edge IC addition we shift left by 1 to align the middle IC terms with the correct bit and add normally
        - *Note: this extra bit alters the original truncated multiplier shifting in the accumulate stage; we must shift one extra bit each time to account for the extra guard bit added for the IC term alignmnet to preserve prior weighting for each column*

## Impulse Response

![Impulse Response](impulse_response.png)

The DUT output (red) overlaid on the ideal fixed-point coefficients (blue).

## Step Response

![Step Response](step_response.png)

The DUT step response (red) vs Python lfilter (blue). The FIR fills in over 28 taps and then converges to the expected steady state step response.

## Frequency Response

![Frequency Response](freq_response.png)

The frequency response of the 12-bit fixed-point model (Q12.0 samples, Q1.11 coeffcients) vs the Python ideal model (floating-point). Frequency respone generated with 50-60KHz band-pass coeffcients.

## Noisy Sine Filtering

![Noisy Sine Filtering](noisy_sine_comparison.png)

A 2kHz sinusoid with added Gaussian noise filtered by the DUT with low-pass coeffcients (10KHz) vs the Python lfilter model.