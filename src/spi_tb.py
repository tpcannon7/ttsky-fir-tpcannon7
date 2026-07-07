import cocotb
from cocotb.triggers import RisingEdge, FallingEdge
from cocotb.clock import Clock

async def spi_transact(dut, data_in):
    data_out = 0x00
    dut.cs_n.value = 0
    await RisingEdge(dut.sclk)
    for i in range(8):
        dut.mosi.value = (data_in & 0x80) >> 7
        await RisingEdge(dut.sclk)
        out = int(dut.miso.value)
        data_out = (data_out << 1) | out
        data_in = data_in << 1

    return data_out


@cocotb.test()
async def test_spi(dut):
    sclk = Clock(dut.sclk, 10, "ns")
    cocotb.start_soon(sclk.start())

    dut.rst_n.value = 0
    await RisingEdge(dut.sclk)
    await RisingEdge(dut.sclk)
    dut.rst_n.value = 1
    await RisingEdge(dut.sclk)

    data = 0xA5
    
    out = await spi_transact(dut, data)
    await RisingEdge(dut.sclk)

    out2 = await spi_transact(dut, data)

    assert out2 == data, f"out = {out2:x}, data = {data:x}"
