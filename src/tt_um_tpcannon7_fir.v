/*
 * Copyright (c) 2026 Trevor Cannon
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_tpcannon7_fir (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  // All output pins must be assigned. If not used, assign to 0.
  assign uio_out[6:5] = 0;
  assign uio_out[2:0] = 0;
  assign uio_oe = 8'b10011000;

  wire [7:0] din_eff;
  wire load_en_eff, in_valid_eff, out_ready_eff, byte_sel_eff;

  // change based on if test mode or not
  assign din_eff = uio_in[6] ? test_dout : ui_in;
  assign load_en_eff = uio_in[6] ? test_load_en : uio_in[0];
  assign in_valid_eff = uio_in[6] ? test_in_valid : uio_in[1];
  assign out_ready_eff = uio_in[6] ? test_out_ready : uio_in[2];
  assign byte_sel_eff = uio_in[6] ? test_byte_sel : uio_in[5];

  fir_filter #(
      .Taps(16)
  ) fir (
      .clk(clk),
      .rst_n(rst_n),
      .din(din_eff),
      .dout(uo_out),
      .load(load_en_eff),
      .in_valid(in_valid_eff),
      .out_ready(out_ready_eff),
      .in_ready(uio_out[3]),
      .out_valid(uio_out[4]),
      .byte_sel(byte_sel_eff)
  );

  wire [7:0] test_dout;
  wire test_load_en, test_byte_sel, test_in_valid, test_out_ready;

  on_chip_test #(
      .Taps(16),
      .SampleWidth(16),
      .CoeffWidth(16)
  ) test_module (
      .clk(clk),
      .rst_n(rst_n),
      .dut_in_ready(uio_out[3]),
      .dut_out_valid(uio_out[4]),
      .test_en(uio_in[6]),
      .test_byte_sel(test_byte_sel),
      .test_in_valid(test_in_valid),
      .test_out_ready(test_out_ready),
      .test_load_en(test_load_en),
      .dout(test_dout),
      .dut_dout(uo_out),
      .test_pass(uio_out[7])
  );

  // List all unused inputs to prevent warnings
  wire _unused = &{uio_in[7], uio_in[4:3], ena, 1'b0};

endmodule
