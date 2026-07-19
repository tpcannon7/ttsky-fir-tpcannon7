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
