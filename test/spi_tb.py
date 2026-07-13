import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, Timer, ClockCycles
from cocotb.clock import Clock

async def spi_transact(dut, data_in, sclk):
    din = data_in
    data_out = 0x00
    dut.cs_n.value = 0
    await RisingEdge(dut.clk)
    cocotb.start_soon(sclk.start())
    for i in range(16):
        dut.mosi.value = (data_in & 0x8000) >> 15
        await RisingEdge(dut.sclk)
        out = int(dut.miso.value)
        data_out = (data_out << 1) | out
        data_in = data_in << 1

    await FallingEdge(dut.sclk)
    sclk.stop()
    
    dut.cs_n.value = 1
    await ClockCycles(dut.clk, 25)

    return data_out

@cocotb.test()
async def test_spi(dut):
    clk = Clock(dut.clk, 40, "ns")
    cocotb.start_soon(clk.start())
    sclk = Clock(dut.sclk, 1000, "ns")

    dut.rst_n.value = 0
    dut.cs_n.value = 1
    dut.mosi.value = 0
    dut.sclk.value = 0
    dut.tx_data_in.value = 0x5C5C
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 10)

    data = 0x5C5C

    out = await spi_transact(dut, data, sclk)
    cocotb.log.info(f"sent = {data}, got = {out}")

    out2 = await spi_transact(dut, data, sclk)
    cocotb.log.info(f"sent = {data}, got = {out2}")
