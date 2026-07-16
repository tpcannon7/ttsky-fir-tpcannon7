# Changelog

## Uncommitted (2026-07-16)

### Fixes
- **Impulse response plot**: Moved from `test_negative_impulse_response` (negative impulse,
  output ≈ -coeffs) into the positive impulse test, fixing spurious `-2*coeffs` errors
  in the plot (up to -468 LSB at mid taps)
- **Step response assertion**: Replaced `abs(out[-1] - expected) <= 30` with per-sample
  `abs(out[i] - y_lfilter_int[i]) <= 30`, catching the overflow at sample 48
- **cs_n assert mid frame assertion**: Fixed `abs(abs())` → signed comparison

### Hardware
- **fir_filter.v mac_idx counter**: Gated increment with `!mac_cnt_full` to prevent
  out-of-bounds read of `samples[28]`/`coeff[28]` (X in waveform)
- **fir_filter.v output saturation**: Replaced raw bit-slice `acc[14:3]` with guard-bit
  overflow detection/clamping to ±2047. Previously the step response wrapped to -2048
  during transient when accumulator exceeded 12-bit signed range

### Code quality
- Deleted dead test files `test/spi_tb.py`, `test/test.py`
- Removed stale Baugh-Wooley comments from `src/trunc_mult.v`
- Added try/except around `plt.savefig()` in all plot tests

### Tests
- Refactored `SPIinterface` into `_transmit`, `transfer`, `transfer_bad` methods
- Added `plots` target to `test/Makefile` (outputs to `docs/`)
- All 10 tests pass, plots regenerated

### Documentation
- `docs/info.md`: SPI timing diagram, RP2040 C bringup snippet, NOP frame explanation,
  quantization error note, coefficient reverse-loading order, Frequency Response section,
  Noisy Sine section
- `README.md`: Added "Results" section with plot thumbnails/captions

---

## 2026-07-15 — b1eeb34

- Updated some docs + new tests

- Added `spi.v` MISO tristate control, mid-frame cs_n fault injection tests
- Full test suite: impulse, negative impulse, step, noisy sine, switching inputs,
  frequency response, non-symmetric coeffs, mid-sample coeff reload,
  cs_n mid-frame fault, coeff reload
- `SPIinterface.transfer_bad` fault-injection method

## 2026-07-14 — 8cb63c6

- Coeff reload test (load coeffs, verify impulse, reload different coeffs, verify)
- Formatting fixes, comments, full 10-test suite

## 2026-07-14 — 9cdd821

- Renamed `spi_slave.v` → `spi.v`
- `test_cs_n_assert_mid_frame` test for SPI fault recovery
- Config updates

## 2026-07-14 — 8164e8b

- Tap count 30→28 (improves timing/utilization)
- Config updates

## 2026-07-14 — 4f78bbc

- System clock 28MHz, higher density

## 2026-07-14 — 86b205a

- SNR improved: 38dB → 51dB
- `DropBits` 11→8 in trunc_mult (retains more precision)

## 2026-07-13 — 6962130

- Bugfix for coefficient load serial output alignment

## 2026-07-13 — 20421a7

- Major test reorg: SPIinterface class, separated tests, removed dead code

## 2026-07-13 — 5f39521..6bd2494

- Successive parameter sweeps for taps (24→28→30→32) and density (60%→80%)
- 12-bit data width throughout

## 2026-07-13 — 671eefa

- Reverted to 12-bit signed multipliers (2×2 tile)
- density sweeps: 50%, 55%, 65%, 70%, 75% across consecutive commits

## 2026-07-12 — 7a147a8

- Cleaned up synthesis warnings in spi_slave.v and top-level

## 2026-07-13 — 98a3a64

- Downshifted from 16-bit to 12-bit signed data path
- Changed width params across control, fir_filter, spi, trunc_mult

## 2026-07-12 — ed7f6b8

- SPI module functional: full duplex, mode detection, coefficient/sample framing
- Removed `new.md` (design notes incorporated elsewhere)
- First working end-to-end flow

## 2026-07-06..2026-07-09 — SPI refactor phase

- **f2c258d** (Jul 6): Replaced on_chip_test parallel interface with SPI (`spi.v`)
- **f8ad465** (Jul 7): Renamed `spi.v` → `spi_slave.v`, cleaned up state machines
- **ee5d29d** (Jul 8): Added `control.v` bridge layer between SPI and FIR
- **274acb5** (Jul 9): New SPI framing method (mode pin for coeff vs sample), CDC sync,
  reduced testbench complexity

## 2026-07-04 — 73c0886

- Added `on_chip_test.v`: BIST-style module for standalone testing
- State machine handshake improvements in fir_filter

## 2026-07-04 — 3192860

- Tap count 16→32 for improved filter response
- Coefficient shift register replaced mux-select with counter (cleaner RTL)

## 2026-07-03 — 720d111

- New tests: noisy sine, step response, frequency response
- `trunc_mult.md` moved to `docs/`
- Removed standalone trunc_mult testbench

## 2026-06-30..2026-07-01 — trunc_mult development

- **527629d** (Jun 30): Baugh-Wooley signed multiplier with error compensation
- **62d0cdd** (Jun 30): Truncated multiplier integration, standalone testbench
- **86abc1e** (Jul 1): Documentation, GL sim fixes, corrected compensation terms

## 2026-06-29..2026-07-04 — FIR state machine evolution

- **1829d96** (Jul 1): Proper handshake protocol (in_ready/out_valid) between FIR and control
- **c5969d7** (Jul 1): Simplified state machine (removed redundant states)
- **8c4aba5** (Jul 1): Fixed loop index integer driver synthesis issue
- **f538131** (Jul 4): Coefficient loading via shift register instead of mux-select

## 2026-06-21..2026-07-13 — Density / config exploration

- Multiple commits sweeping density (60%→80%) and clock speeds (25MHz→28MHz)
- 1×2 vs 2×2 tile configurations
- Gate-level simulation fixes

## 2026-06-05..2026-06-19 — Early development

- Initial commit: Tiny Tapeout project scaffold, cocotb test framework
- FIR filter with loading state machine, parallel interface
- MAC index counter, sample/coeff shift registers, trunc_mult block
- First working impulse response in simulation

## 2026-06-05 — Project setup

- `.devcontainer/`, `.github/workflows/`, `.vscode/` config
- `src/fir_filter.v`, `src/trunc_mult.v` initial implementations
- `test/tb.v`, `test/fir_tb.py` cocotb testbench
- `docs/info.md`, `README.md`, `info.yaml`, `LICENSE`
