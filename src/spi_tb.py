import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, Timer
from cocotb.clock import Clock

async def spi_transact(dut, data_in, sclk):
    din = data_in
    data_out = 0x00
    dut.cs_n.value = 0
    await Timer(5, "ns")
    sclk.start()
    for i in range(8):
        dut.mosi.value = (data_in & 0x80) >> 7
        await RisingEdge(dut.sclk)
        out = int(dut.miso.value)
        data_out = (data_out << 1) | out
        data_in = data_in << 1

    await FallingEdge(dut.sclk)

    cocotb.log.info(f"rx_byte = {int(dut.rx_byte.value):x}, data_in = {din:x}")
    assert dut.rx_byte.value == din, f"RX got {int(dut.rx_byte.value):02x}, expected {din}"

    sclk.stop()
    dut.cs_n.value = 1
    await Timer(10, "ns")

    return data_out

@cocotb.test()
async def test_spi(dut):
    dut.sclk.value = 0
    dut.cs_n.value = 1
    dut.mosi.value = 1
    await Timer(20, "ns")

    sclk = Clock(dut.sclk, 10, "ns")

    data = 0xA5
    
    out = await spi_transact(dut, data, sclk)

    cocotb.log.info(f"out = {out:x}")
    assert out == 0x5C