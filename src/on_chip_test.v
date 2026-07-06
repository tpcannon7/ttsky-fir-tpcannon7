`default_nettype none

module on_chip_test #(
    parameter Taps = 16,
    parameter CoeffWidth = 16,
    parameter SampleWidth = 16
) (
    input wire clk,
    input wire rst_n,
    input wire test_en,
    input wire dut_out_valid,
    input wire dut_in_ready,
    input wire [7:0] dut_dout,

    output wire test_byte_sel,
    output wire test_load_en,
    output wire test_in_valid,
    output wire test_out_ready,
    output wire test_pass,
    output wire [7:0] dout
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



  //////
  // ----------------->
  // fix the sync issues from using async pins on rp2040
  // double flop synchronize control signals, fix byte_sel pulse issue that stems from same async pin issue
  // finish the test module
  // need to also change load signal to a pulse to start load state not beign held high the whole time
  // see markdown file in the other chat for further notes
  // ----------------->
  ///////



  // 10Khz low pass coeffcients (double check)
  localparam [(CoeffWidth*Taps)-1:0] StaticCoeffs = {
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

  wire [CoeffWidth-1:0] static_coeff_array[0:Taps-1];
  genvar i;
  generate
    for (i = 0; i < Taps; i++) begin
      assign static_coeff_array[i] = StaticCoeffs[(i*CoeffWidth)+:CoeffWidth];
    end
  endgenerate

  // verify this is correct impulse amplitude and # of samples = # of taps
  localparam [(SampleWidth*Taps)-1:0] ImpulseSamples = {
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
    16'd0,
    16'd32767
  };

  wire [SampleWidth-1:0] impulse_sample_array[0:Taps-1];
  genvar j;
  generate
    for (j = 0; j < Taps; j++) begin
      assign impulse_sample_array[j] = ImpulseSamples[(j*SampleWidth)+:SampleWidth];
    end
  endgenerate

  // +1 to account for doubling to 32 (5 bit) indexing to low and high byte transmission
  // theres maybe a better way to do this
  reg [$clog2(Taps)+1:0] coeff_load_cnt, sample_load_cnt;

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      coeff_load_cnt <= 0;
    end else if (curr_st == TestLoadCoeff) begin
      coeff_load_cnt <= coeff_load_cnt + 1'b1;
    end else begin
      coeff_load_cnt <= 0;
    end
  end

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      sample_load_cnt <= 0;
    end else begin
      sample_load_cnt <= sample_load_cnt;
    end
  end

endmodule
