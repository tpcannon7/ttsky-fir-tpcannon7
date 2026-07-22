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

Run plot-only/optional tests:
```
FIR_TB_PLOTS=1 make -B
```

Generate plots from test suite:
```
make plots
```
