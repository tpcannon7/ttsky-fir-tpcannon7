module on_chip_test #(
    parameter Taps = 16,
    parameter CoeffWidth = 16,
    parameter SampleWidth = 16
) (
    input wire clk,
    input wire rst_n,

    // state machine and counter i/o?

    output wire [7:0] out
);

  // idea is to load coeffcients through same itnerface as regular, using these static coeffcients
  // expose a port outptu on this for that or something and send them through the same interface on upper level module

  // samples same idea send through same interface (no byte reconstruct? should actually do it same both ways
  // add it same there or somethign as a good test of low vs. high logic)
  // we'll send impulse same from here as first sample so we can make samples localparam that is a impulse test same as cocotb

  // we cna probbaly make two internal test states TestLoadCOeff and then TestDriveSamples, we can load coeffs once and then stay in TestDriveSampels until Test pin
  // de asserted? or maybe force a async reset out of this back to a known zero state

  // use counters for coeff indexing and sample indexing/looping
  // log2(Taps*2) perhaps to accoutn for high/low byte enabling

  // 10Khz low pass coeffcients (double check)
  localparam [CoeffWidth-1:0] StaticCoeffs[0:Taps-1] = {
    16'd314,
    16'd473,
    16'd921,
    16'd1586,
    16'd2353,
    16'd3089,
    16'd3666,
    16'd3983,
    16'd3983,
    16'd3666,
    16'd3089,
    16'd2353,
    16'd1586,
    16'd921,
    16'd473,
    16'd314
  };

  // verify this is correct impulse amplitude and # of samples = # of taps
  localparam [SampleWidth-1:0] ImpulseSamples[0:Taps-1] = {
    16'd32767,
    16'd0,
    16'd0,
    16'd0,
    16'd0,
    16'd0,
    16'd0,
    16'd0,
    16'd0,
    16'd0,
    16'd0,
    16'd0,
    16'd0,
    16'd0,
    16'd0,
    16'd0
  };





endmodule
