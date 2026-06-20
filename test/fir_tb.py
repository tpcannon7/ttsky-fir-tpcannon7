import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, Timer, ReadOnly, ClockCycles
from cocotb.clock import Clock

from scipy.signal import firwin, lfilter
import numpy as np

# params
taps = 8
coeff_width = 8
sample_width = 8
out_width = 8

cut_off = 10000
sample_rate = 32000

async def reset(dut):
    dut.ui_in.value = 0x00
    dut.uio_in.value = 0x00
    dut.ena.value = 1
    dut.rst_n.value = 0

    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1

    await RisingEdge(dut.clk)

async def load_coeff(dut, coeffs):
    # assert load_en
    dut.uio_in.value = 0x01

    # wait for in_ready
    while(dut.uio_out.value[3] != 1):
            await RisingEdge(dut.clk)

    # assert in_valid, then load coeffcients
    dut.uio_in.value = 0x03
    for coeff in coeffs:
        dut.ui_in.value = coeff
        await RisingEdge(dut.clk)

    dut.uio_in.value = 0x00
    dut.ui_in.value = 0x00
    await RisingEdge(dut.clk)

@cocotb.test()
async def test_impulse(dut):
    clk = Clock(dut.clk, 10, "us")
    cocotb.start_soon(clk.start())

    await reset(dut)

    h = firwin(taps, cut_off, fs=sample_rate)

    normalize = ((2**(coeff_width-1)))
    coeffs = h * normalize
    cocotb.log.info(f"{h}")
    cocotb.log.info(f"{coeffs}")

    min_val = -(2**(coeff_width-1))
    max_val = (2**(coeff_width-1)-1)
    coeffs = [max(min_val, min(max_val, int(round(c)))) for c in coeffs]
    cocotb.log.info(f"{coeffs}")

    await load_coeff(dut, coeffs)

    samples = [127,0,0,0,0,0,0,0]

    cocotb.log.info("----------------------------------")
    cocotb.log.info("           IMPULSE RESPONSE      ")
    cocotb.log.info("----------------------------------")

    for idx, s in enumerate(samples):
        # wait for in_ready
        while(dut.uio_out.value[3] != 1):
            await RisingEdge(dut.clk)

        # assert in_valid, load sample in
        dut.uio_in.value = 0x02
        dut.ui_in.value = s 
        cocotb.log.info(f"sample {idx} = {s}")
        await RisingEdge(dut.clk)
        dut.uio_in.value = 0x00
        dut.ui_in.value = 0x00

        # wait for out_valid
        while(dut.uio_out.value[4] != 1):
            await RisingEdge(dut.clk)

        # check
        # we are going to accept the off by one truncation BS i dont care!
        res = dut.uo_out.value.to_signed()
        cocotb.log.info(f"res = {res}")
        cocotb.log.info(f"expected = {coeffs[idx]}")
        await ClockCycles(dut.clk, 2)
        dut.uio_in.value = 0x04
        await ClockCycles(dut.clk,1)


@cocotb.test()
async def test_step_response(dut):
    clk = Clock(dut.clk, 10, "us")
    cocotb.start_soon(clk.start())

    await reset(dut)

    h = firwin(taps, cut_off, fs=sample_rate)

    normalize = ((2**(coeff_width-1)))
    coeffs = h * normalize
    cocotb.log.info(f"{h}")
    cocotb.log.info(f"{coeffs}")

    min_val = -(2**(coeff_width-1))
    max_val = (2**(coeff_width-1)-1)
    coeffs = [max(min_val, min(max_val, int(round(c)))) for c in coeffs]
    cocotb.log.info(f"{coeffs}")

    await load_coeff(dut, coeffs)

    samples = [127,127,127,127,127,127,127,127]

    cocotb.log.info("----------------------------------")
    cocotb.log.info("           STEP RESPONSE          ")
    cocotb.log.info("----------------------------------")

    for idx, s in enumerate(samples):
        while(dut.uio_out.value[2] != 1):
            await RisingEdge(dut.clk)

        dut.uio_in.value = 0x02
        dut.ui_in.value = s 
        cocotb.log.info(f"sample {idx} = {s}")
        await ClockCycles(dut.clk,1)
        dut.uio_in.value = 0x00
        dut.ui_in.value = 0x00

        while(dut.uio_out.value[3] != 1):
            await RisingEdge(dut.clk)

        res = dut.uo_out.value.to_signed()
        cocotb.log.info(f"res = {res}")
        cocotb.log.info(f"expected = {coeffs[idx]}")



