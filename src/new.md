# FIR Filter — SPI Interface Design Spec
 
*Working reference for RTL build. Captures the architecture decided before implementation.*
 
---
 
## 1. System overview
 
A 16-tap FIR filter exposed as an SPI **device** (slave) on a Tiny Tapeout tile.
The host (RP2040 on the TT demo board) loads coefficients, streams samples in, and
reads results back — all over a standard 4-wire SPI bus.
 
**Guiding principle:** push the contract onto the host, keep the silicon simple.
The host conforms to a documented protocol; the chip does not add defensive logic
to tolerate the host misbehaving.
 
### Dataflow
 
```
        MOSI                                                    MISO
host ──────►  SPI front-end ──► FIFO ──► FIR filter ──► result reg ──► SPI ──► host
              (oversampled     (sync,   (unchanged      (single
               in clk domain)  ~2 deep)  verified core)  register)
```
 
Each block owns one concern. Transport (SPI) is decoupled from compute (FIR) by the
FIFO on the input and the result register on the output.
 
---
 
## 2. Clocking
 
| Clock | Rate | Source | Role |
|-------|------|--------|------|
| `clk` | ~30 MHz | RP2040 → TT `clk` pin | Core heartbeat: MAC, FIFO, everything |
| `SCK` | ~2–4 MHz | RP2040 SPI/PIO peripheral (divided down) | SPI bit clock only |
 
**Single clock domain.** `SCK`, `MOSI`, `CS` are **oversampled** into the `clk` domain
(2-flop synchronizers + edge detection). Nothing runs on `SCK` directly, so there is
**no CDC and no async FIFO**.
 
- `SCK` must stay ≥ ~4× below `clk` for clean edge detection. With `clk`=30 MHz, keep
  `SCK` ≤ ~5–7 MHz. Target 2–4 MHz for margin.
- `SCK` is **not** the RP2040 core rate (200 MHz) — it is divided down. Never run it near core speed.
---
 
## 3. Pinout (TT Pmod SPI convention, top row)
 
| Pin | Signal | Direction | `uio_oe` |
|-----|--------|-----------|----------|
| `uio[0]` | CS (active low) | input | 0 |
| `uio[1]` | MOSI | input | 0 |
| `uio[2]` | MISO | output | 1 (or `~cs_n` to tri-state when idle) |
| `uio[3]` | SCK | input | 0 |
 
**Freed pins** (big win vs. the old parallel interface): all 8 `ui_in` and all 8
`uo_out` are now available for sidebands — test-mode enable, fault/status flag,
data-ready line, etc.
 
---
 
## 4. SPI mode — locked decisions
 
These are coin-flips that only hurt if left ambiguous. Fixed:
 
- **Mode 0** — CPOL=0, CPHA=0. Clock idles low; sample on **rising** edge, shift on falling.
- **MSB-first** bit order.
- **Oversampled** in `clk` domain (not clocked on `SCK`).
- **CS-framed** — CS falling = start of transfer (reset counters, expect command byte);
  CS rising = transfer done (reset framing).
### Front-end skeleton (oversampled)
 
```
- synchronize sck, mosi, cs_n into clk domain (2 flops each)
- detect sck rising edge:  sck_sync 0 -> 1  = "sample edge"
- on cs_n falling:         reset bit/byte counters, state = EXPECT_CMD
- on each sample edge:     shift mosi_sync into shift_reg, bit_count++
- at bit_count == 8:       byte complete -> route by state (cmd? coeff? sample?)
- on cs_n rising:          transfer complete, reset framing
```
 
Everything downstream (command decode, byte-pair assembly, FIFO write) hangs off
"byte complete."
 
---
 
## 5. Protocol
 
### Command byte
 
First byte after CS falls is a **command / opcode** (out-of-band signaling by position,
not a magic data value). Suggested field layout:
 
| Bits | Field | Meaning |
|------|-------|---------|
| 7 | R/W | 0 = write to chip, 1 = read from chip |
| 6 | target | 0 = coefficient, 1 = sample |
| 5:0 | addr / index / unused | register address or index |
 
The single `target` bit is the entire coeff-vs-sample distinction that used to be a
whole `byte_sel` pin + buffer + mux. Gone.
 
### Framing style: command + burst
 
Send one command, then stream many payload words under a single CS assertion.
Amortizes the command-byte overhead to ~nothing over a long sample stream.
 
**Load 16 coefficients:**
```
CS low
  CMD (write, target=coeff)
  coeff[0] low byte, coeff[0] high byte
  coeff[1] low byte, coeff[1] high byte
  ... x16
CS high
```
 
**Stream samples (full-duplex):**
```
CS low
  CMD (write, target=sample)
  sample[n] low, sample[n] high   <-- MOSI in;  result[n-1] shifts out on MISO
  sample[n+1] low, high           <-- and so on
CS high
```
 
> Byte order (low-then-high) is a **datasheet contract**. If the host sends it wrong,
> that's a host bug, not a silicon problem. No reordering logic on-chip.
 
---
 
## 6. Config / status register
 
Host writes **intent**, FIR reads it as an input and runs its **own** FSM.
The register is a mailbox the FIR checks — **not** a remote control into its state machine.
 
**Control (host writes):** mode, go/stop, soft reset, tap count.
**Status (host reads over MISO):** ready, FIFO full/empty/overflow, current mode, result-ready.
 
The readable status register is your bring-up observability — most of what the
deferred on-chip test would have told you, available on demand.
 
---
 
## 7. Full-duplex output (why there's no output FIFO)
 
One transfer = one sample **in** on MOSI + previous result **out** on MISO,
simultaneously. Input and output rates are therefore inherently matched — every input
has exactly one corresponding output. The output side needs only a **single result
register**, not a FIFO.
 
Design carefully:
- **First transfer**: no result exists yet → send dummy/zero on MISO (standard SPI behavior).
- **Latch timing**: capture the FIR's completed result into the output register at the
  **start** of a transfer, so it's stable during shift-out. Do not latch mid-shift (tearing).
---
 
## 8. Buffers
 
| Buffer | Type | Depth | Why |
|--------|------|-------|-----|
| Input FIFO | synchronous (single clock domain) | ~2 | Decouple SPI-in from MAC; absorb bursts |
| Output | single register | 1 | Full-duplex framing matches rates; no FIFO needed |
 
**Overflow policy** (input FIFO full, another sample arrives): datasheet contract
("don't exceed rate R") + optional `ready` sideband pin as a safety net. Do **not**
silently drop — a dropped sample corrupts FIR math.
 
> Note: async (dual-clock) FIFO is **not** used. It was a flex that would roughly double
> the flop count of a shallow FIFO for CDC safety you don't need once oversampled.
 
---
 
## 9. Timing budget (sanity check)
 
At `clk`=30 MHz, `SCK`=2 MHz, ~20-cycle serial MAC:
 
- MAC produces a result every ~670 ns (~1.5 MHz).
- One 16-bit SPI transfer takes ~8 µs.
- FIR finishes ~12× faster than the transfer cadence → result always ready before read. ✓
**Rule that must hold:** `(bits_per_transfer / SCK) > MAC_latency`. Satisfied with wide margin.
 
- **Throughput** (sample rate) ≈ 125 kHz — limited by *SPI transport*, not the MAC.
- **Latency** ≈ one transfer (result for sample *n* comes out during transfer *n+1*) + MAC time.
- Clears audio (44.1–192 kHz) and essentially all sensors with headroom. The MAC loafs.
To go faster later: raise `SCK` (until oversampling cap) or widen the interface —
**not** speed up the MAC.
 
---
 
## 10. Area notes
 
From current synth (16 taps, 16-bit): 546 flops, 52% utilization, ~35% cell-growth
headroom before the routing ceiling.
 
- Dominant cost is the datapath: ~256 coeff flops + ~256 delay-line flops + the ~530
  mux2 tap-selection tree. The interface is rounding error next to it.
- SPI/FIFO swap is roughly **net-neutral**: removes the 7 `_eff` muxes + byte_sel logic,
  adds SPI shift-reg + small sync FIFO.
- No SRAM/RAM macro available at this tile size — storage stays in flops.
- If area ever bites: **transposed-form FIR** eliminates the big tap-select mux
  (distributed adders instead). Don't do it now; it's the drawer to open later.
---
 
## 11. Scope / deferred
 
- **On-chip self-test: deferred.** Not because it won't fit — because a real SPI
  interface lets you drive impulse-response tests from the RP2040 in host software,
  which absorbs most of its value. Deliberate scope call.
- **FIR core: unchanged.** MAC, Q1.15 math, coefficient storage, and the passing
  impulse-response cocotb test all stay verified. Only the front door changed.
---
 
## 12. Build order
 
1. **SPI front-end** — mode 0, MSB-first, oversampled, CS-framed. Get **one byte**
   received correctly in a cocotb testbench that acts as an SPI master. That's ~80% of
   the battle.
2. Command decode + byte-pair assembly.
3. Input FIFO (synchronous) + wire to FIR input.
4. Result register + MISO shift-out (full-duplex).
5. Config/status register.
6. Re-run existing impulse-response test end-to-end over the SPI path.
Write the module yourself — the SPI slave is small (~40–60 lines) and the learning is
in the shift-register + edge-detect logic.
