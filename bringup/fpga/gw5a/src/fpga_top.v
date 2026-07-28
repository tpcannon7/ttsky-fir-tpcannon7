`default_nettype none

module fpga_top (
    input wire clk,
    input wire rst_n,

    input  wire sclk,
    input  wire cs_n,
    input  wire mosi,
    output wire miso,

    input wire fir_mode
);

  // make sure to add to fir_filter.v:
  // reg signed [CoeffWidth-1:0] coeff[0:Taps-1]; /*synthesis syn_preserve = 1*/
  // reg signed [SampleWidth-1:0] samples[0:Taps-1]; /*synthesis syn_preserve = 1*/

  // new_trunc_mult.v port header: /*synthesis syn_dspstyle="logic" */

  wire [7:0] ui_in, uio_in, uio_out, uo_out, uio_oe;
  wire clk_40mhz;

  assign ui_in = {7'b0, fir_mode};
  assign uio_in[0] = cs_n;
  assign uio_in[1] = mosi;
  assign uio_in[2] = 1'b0;
  assign uio_in[3] = sclk;
  assign uio_in[7:4] = 4'b0;

  assign miso = uio_out[2];

  tt_um_tpcannon7_fir tt_dut (
      .clk(clk_40mhz),
      .rst_n(rst_n),
      .ena(1'b1),
      .ui_in(ui_in),
      .uio_in(uio_in),
      .uio_out(uio_out),
      .uo_out(uo_out),
      .uio_oe(uio_oe)
  );

  Gowin_PLL pll (
      .clkin  (clk),
      .clkout0(clk_40mhz),
      .mdclk  (clk)
  );


endmodule

`default_nettype wire
