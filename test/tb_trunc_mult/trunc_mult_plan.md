# trunc_mult: Test, Plot, and Area Plan

## Current Status

### What works
- `trunc_mult_tb.py` runs 20 random signed pairs (a×b, 12-bit), yielding 400 comparisons per DropBits
- Compares `trunc_out[k]` vs `golden_ref >> k` for DropBits 0..11
- Assertion: `abs(diff) <= 2` (in truncated-output LSBs) — a correctness gate, NOT an error characterization
- **Proven**: Removing IC error correction (comment lines 137–139 in `trunc_mult.v`) causes assertion failure at DropBits≥4

### The assertion is a regression gate, not a metric
The `<= 2` threshold, matching Garafolo et al. ±2 LSB bound, flags behavioral regressions (e.g. bit-width mismatches, incorrect IC logic). It does NOT tell you how much absolute error grows with DropBits, nor how area shrinks. Those are the purpose of the statistics + area plan below.

---

## Planned Additions

### 1. Error Statistics Collection

**Purpose**: Unlike the assertion (which gates correctness in truncated-output LSBs), this collects the *absolute* error magnitude in full-precision LSBs to quantify the cost of higher DropBits.

**File**: `trunc_mult_tb.py` (extend)

Add env-var-controlled large run (e.g. `COCOTB_TRUNC_STATS=1` or separate test filter):
- Run ~1000 random input pairs uniformly distributed across signed 12-bit range
- Additionally run a small deterministic set of corner cases: max/min signed (`±2048`), zero, power-of-two (`1, 2, 4, ..., 1024`)
- Record error = `(trunc_out[k] - (golden >> k)) << k` — the error shifted back to full-precision LSBs
- Save per-DropBits to `trunc_mult_stats.csv`:

```
drop_bits,max_abs_error,mean_abs_error,rms_error,num_samples
0,2,0.12,0.22,1040
...
11,4096,2048.3,2350,1040
```

Units: full-precision LSBs (error `(trunc_out[k] - (golden >> k)) << k` is shifted back before CSV write).

Per-sample error does NOT need to be saved to CSV — the aggregates are sufficient for the tradeoff plot. (Per-sample data can be kept in-memory for histogram/violin subplots later.)

### 2. Area Estimation

#### Option A: Yosys generic cells (quick, no deps)
- **File**: `synth_area.sh`
- Loop DropBits 0..11:
  ```
  yosys -p "
    read_verilog src/trunc_mult.v;
    hierarchy -chparam DropBits $i -chparam DataWidth 12 -top trunc_mult;
    synth -top trunc_mult;
    stat
  "
  ```
  - Parse "Number of cells" from `stat` output
- Save `trunc_mult_area.csv`:

```
drop_bits,cells
0,1234
1,1156
...
11,456
```

#### Option B: Sky130 PDK cells (real µm² area)
- Ciel already installed sky130A pdk at `~/.ciel/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib`
  - Yosys can run via `yosys -l <logfile> -c synth_trunc_mult.tcl`
  - **But**: `-c` scripts don't support `hierarchy -chparam`, so loop DropBits with a wrapper shell script that generates parameterized yosys commands on the fly
- Add ABC tech mapping to yosys flow:

```
yosys -p "
  read_verilog src/trunc_mult.v;
  hierarchy -chparam DropBits \$i -chparam DataWidth 12 -top trunc_mult;
  synth -top trunc_mult;
  abc -liberty ~/.ciel/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib;
  stat -liberty ~/.ciel/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
"
```
- The `$i` is shell-expanded by the wrapper loop before yosys sees it
- Parses "Chip area" (µm²) instead of cell count
- Also gives cell-type breakdown (AND2, AOI21, etc.) from `stat`

**Recommendation**: Start with Option A, upgrade to B later by swapping the CSV.

### 3. Tradeoff Plot

**File**: `plot_tradeoff.py`

Reads both CSVs, produces two-panel figure using matplotlib:

Implementation:
- `pyplot.subplots(2, 1, sharex=True)`, figure size ~8"×6"
- **Top panel**: plot `drop_bits` vs `max_abs_error` (solid line) and `mean_abs_error` or `rms_error` (dashed), semi-log y-scale (`set_yscale('log')`)
  - y-label: "Max |error| (full LSB)"
- **Bottom panel**: plot `drop_bits` vs `cells` (or µm² if using Option B), linear y-scale
  - y-label: "Area (cells)"
- Shared x-axis: "DropBits"
- Vertical dashed line (`axvline(x=8, linestyle='--', color='gray')`) marking the chosen design point
- Save to `trunc_mult_tradeoff.png`

Layout sketch:

```
┌───────────────────────────────────────────────────┐
│  Max absolute error (full-precision LSBs)   log y │
│  ──────────────────────────────────────           │
│  │e│  (grows ~2^DropBits)                        │
│  │r│                                              │
│  │r│  Vertical dashed line at DropBits=8          │
│  │o│                                              │
│  │r│                                              │
│  └──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──►            │
│   0  1  2  3  4  5  6  7  8  9  10 11             │
│                                                    │
│  Area (cells or µm²)                        linear │
│  ──────────────                                    │
│  │                                               │ │
│  │c│  (shrinks as columns drop)                   │ │
│  │e│                                              │ │
│  │l│                                              │ │
│  │l│                                              │ │
│  │s│                                              │ │
│  └──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──►            │
│   0  1  2  3  4  5  6  7  8  9  10 11             │
└───────────────────────────────────────────────────┘
```

Annotations:
- "Error bound: ≤±2 LSB (truncated-output units) at ALL DropBits"

### 4. Makefile Targets

#### `test/tb_trunc_mult/Makefile`

```makefile
.PHONY: stats area plot plots

stats:
	COCOTB_TRUNC_STATS=1 $(MAKE) sim

area: trunc_mult_area.csv

trunc_mult_area.csv:
	bash synth_area.sh

plot: trunc_mult_tradeoff.png

trunc_mult_tradeoff.png: trunc_mult_stats.csv trunc_mult_area.csv
	python3 plot_tradeoff.py

plots: stats area plot
	mv trunc_mult_tradeoff.png ../docs/
```

#### `test/Makefile` (add to existing `plots` target)

```makefile
plots:
	# existing fir_tb plots ...
	+$(MAKE) -C tb_trunc_mult plots
	cp tb_trunc_mult/trunc_mult_tradeoff.png ../docs/
```

---

## Metric Notes & Caveats

### Error per multiply

| DropBits | Output width | Error bound (truncated LSB) | Max abs error (full-precision LSB) |
|----------|-------------|----------------------------|-----------------------------------|
| 0 | 24 bits | ≤±2 | ≤2 |
| 4 | 20 bits | ≤±2 | ≤32 |
| 8 | 16 bits | ≤±2 | ≤512 |
| 11 | 13 bits | ≤±2 | ≤4096 |

The error correction guarantees ≤±2 truncated-output LSBs at *every* DropBits. Absolute error in full-precision LSBs grows because each truncated LSB carries more weight as bits are dropped.

### What the plot tells you — and what it doesn't

The plot shows the engineering tradeoff:
- **Cost**: error grows ~2^DropBits (exponential)
- **Benefit**: area shrinks as columns drop (monotonic)
- **Validation**: IC error correction holds ≤±2 truncated LSBs at every level
- **Design point**: DropBits=8 is marked with a dashed vertical line

The plot does **not** tell you "is DropBits=8 good enough for the FIR filter?" That question is answered by the FIR testbench (`fir_tb.py`), which compares DUT FIR output against a Python floating-point reference model. The `test_noisy_sine` test overlays DUT and Python outputs — already visible in `docs/noisy_sine_comparison.png` — and the two are visually indistinguishable at DropBits=8. The freq response and impulse response plots (`docs/freq_response.png`, `docs/impulse_response.png`) confirm the same.

---

## Future / Optional

- **Cell-type breakdown bars**: Stacked bar chart within each DropBits bar showing AND2, AOI, XOR, etc. counts
- **PDK mapping via volare**: Upgrade option B once PDK is downloaded
- **Error histogram subplot**: Distribution of errors per DropBits (box plot or violin)
