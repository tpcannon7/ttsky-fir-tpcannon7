import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, Timer, ReadOnly, ClockCycles
from cocotb.clock import Clock

drop_bits = 15
data_width = 16
output_width = (data_width * 2)
columns =  output_width - drop_bits

@cocotb.test()
async def mult_test(dut):
    a = -32767
    b = 92

    dut.a.value = a
    dut.b.value = b

    await ReadOnly()

    for i in range(columns):
        pp_array = dut.partial_products[i].value
        sp_array = dut.sum_products[i].value
        cocotb.log.info(f"pp {i} = {pp_array}")
        cocotb.log.info(f"sum_pp {i} = {sp_array}")
        cocotb.log.info("\n")

    out = dut.out.value.to_signed()
    expected = (a*b) >> drop_bits
    cocotb.log.info(f"out = {out}")
    cocotb.log.info(f"expected = {expected}")
