# Changelog

## Uncommitted

- `test/fir_tb.py`: Refactored `test_load_coeffs_mid_sample_drive` — replaced ~140 lines of inline SPI bit-banging with `SPIinterface` calls, added assertions verifying both c1 and c2 impulse responses
- `test/fir_tb.py`: Gated `test_frequency_response` and `test_load_coeffs_mid_sample_drive` behind `@cocotb.test(skip=os.getenv("FIR_TB_PLOTS") is None)` — default `make -B` skips them
- `test/Makefile`: `plots` target now passes `FIR_TB_PLOTS=1`, uses `mv -f`
- `docs/info.md`: Added MISO CS_N-to-SCLK hold time (2 core cycles / 50 ns)
- `src/trunc_mult.v`: Added IC column Baugh-Wooley constraint comment
- `README.md`: Added sampling rate line (~294 kSps @ SCLK = 5 MHz)
- `docs/info.md`: Added CS_N high-time section; updated sampling rate calculation
- `docs/CHANGELOG.md`, `TODO.md`: Updated for current repo state

## 2026-07-19 — f6b01fb

- **Tap count 28→36**: `src/tt_um_tpcannon7_fir.v` `localparam Taps = 36`,
  `src/fir_filter.v` default `parameter Taps = 36`, `test/fir_tb.py` `taps = 36`
- **System clock 25→40 MHz**: `src/config.json` `CLOCK_PERIOD` 40→25 ns,
  `info.yaml` `clock_hz` 25M→40M
- **Docs**: `README.md`, `info.yaml`, `docs/info.md` — all tap count and clock
  references updated; added sampling rate (~294 kSps, ~147 KHz Nyquist) and
  CS_N high-time section to `docs/info.md`
- **Plots**: All 4 response plots regenerated (freq, impulse, step, noisy sine)
- **Changelog**: Recorded 36-tap / 40-MHz transition

## 2026-07-16..2026-07-19 — Overflow fix, test refactor, SPI cleanup, MAC pipeline

### Hardware
- **fir_filter.v output saturation**: Replaced raw bit-slice `acc[14:3]` with guard-bit
  overflow detection/clamping to ±2047. Previously the step response wrapped to -2048
  during transient when accumulator exceeded 12-bit signed range (`03faaf1`)
- **fir_filter.v mac_idx counter**: Gated increment with `!mac_cnt_full` to prevent
  out-of-bounds read of `samples[28]`/`coeff[28]` (X in waveform) (`2ff79c3`)
- **MAC pipeline**: Added 2-cycle/tap pipelined MAC (load operands on cycle N,
  accumulate on cycle N+1), decoupling tap-select mux + multiplier from accumulator
  adder to close timing (`2ff79c3`)
- **MODE → FIR_MODE**: Renamed mode pin for clarity across fir_filter, control, spi
  (`53661a4`)
- **Config sweeps**: Density 70% → 72% → 65%, hold margins 0.1→0.05, tap count
  28→26→28 across multiple commits (`25945bc`, `20944c6`, `083c4d0`, `3f246a9`)

### Testbench
- **New overflow test** (`test_overflow`): monotonicity + final saturation check
  (`a51d6c4`)
- **SPIinterface refactor**: Broke monolithic transmit into `_transmit`, `transfer`,
  `transfer_bad` (fault injection) methods (`53661a4`)
- **Bad-transaction tests**: `transfer_bad` injects random CS_N high mid-frame to
  verify SPI fault recovery (`53661a4`)
- **Coefficient reload test**: Load coeffs, verify impulse, reload different coeffs,
  verify (`a51d6c4`)
- **Seeded RNG**: `FIR_TB_SEED` env var for reproducible test runs (`53661a4`)
- **Mid-sample coefficient reload**: Manual SPI frame construction for exploratory
  test (`a51d6c4`)
- Plot-only tests (`test_frequency_response`, `test_load_coeffs_mid_sample_drive`)
  with try/except around `plt.savefig()` (`03faaf1`, `a51d6c4`)
- Deleted dead test files `test/spi_tb.py` and `test/test.py` (`03faaf1`)
- Added `plots` target to `test/Makefile` (`03faaf1`)
- All 10 tests pass, all 4 plots regenerated across multiple commits

### SPI
- **MISO idle-low**: MISO actively driven LOW during idle instead of tri-stated
  (`53661a4`)
- **negedge sensitivity**: SPI module shifts `tx_buf` on `posedge clk`, fixing
  edge-alignment issues (`53661a4`)
- **cs_n mid-frame fault**: SPI resets on premature CS_N de-assertion, discarding
  partial frame (`53661a4`)

### Code quality
- Removed stale Baugh-Wooley comments from `src/trunc_mult.v` (`03faaf1`)
- Cleaned up synthesis warnings across control, fir_filter, spi (`53661a4`)
- Deleted `test/tb.gtkw` (stale absolute paths) (`53661a4`)

### Documentation
- `docs/info.md`: Complete rewrite — SPI timing diagram, RP2040 C bringup snippet,
  NOP frame explanation, quantization error note, coefficient reverse-loading order,
  Frequency Response section, Noisy Sine section (`03faaf1`, `53661a4`, `a51d6c4`)
- `README.md`: Added "Results" section with plot thumbnails/captions (`03faaf1`)
- `CHANGELOG.md`: Brought up to date with full project history (`03faaf1`)
- Spelling and mode naming consistency pass (`5b897de`)

---

## 2026-07-15 — b1eeb34

- Updated some docs + new tests

- Added `spi.v` MISO idle-low handling (MISO is driven LOW during idle, not tri-stated), mid-frame cs_n fault injection tests
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
