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

  fir_filter #(
      .Taps(16)
  ) fir (
      .clk(clk),
      .rst_n(rst_n),
      .din(uo_out),
      .dout(uo_out),
      .load(uio_in[0]),
      .in_valid(uio_in[1]),
      .out_ready(uio_in[2]),
      .in_ready(uio_out[3]),
      .out_valid(uio_out[4]),
      .byte_sel(uio_in[5])
  );



  // List all unused inputs to prevent warnings
  wire _unused = &{uio_in[7], uio_in[4:3], ena, 1'b0};

endmodule
