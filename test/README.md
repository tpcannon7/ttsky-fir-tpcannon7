# D-FIR Testbench README

Install dependencies:

```
pip install -r requirements.txt
```

Run full RTL simulation test suite:
```
make -B
```

Run single cocotb test:
```
make -B COCOTB_TEST_FILTER=test_impulse_response
```

Run optional test(s):
```
FIR_TB_OPTIONAL=1 make -B
```

Generate plots from test suite:
*Note: does not make plot(s) from tb_trunc_mult/*
```
make plots
```

## Quick Start

Minimal Python example using cocotb's `SPIinterface` helper to load coefficients and send an impulse:

```python
from scipy.signal import firwin

# Generate 50–60 kHz bandpass coefficients for a 36-tap filter
coeffs = [int(round(c * 2048)) for c in firwin(36, [50e3, 60e3], pass_zero=False, fs=294e3)]

await spi.load_coeff(coeffs)

# Send impulse (max positive 12-bit value) followed by zeros
response = await spi.load_samples([2047] + [0] * 35)
# response[2:] should approximately match coeffs (k=2 pipeline lag)
```
