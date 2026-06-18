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
  assign uio_out[7:4] = 0;
  assign uio_out[1:0] = 0;
  assign uio_oe = 8'b00001100;

  fir_filter #(
      .Taps(8)
  ) fir (
      .clk(clk),
      .rst_n(rst_n),
      .din(ui_in),
      .dout(uo_out),
      .load(uio_in[0]),
      .in_valid(uio_in[1]),
      .in_ready(uio_out[2]),
      .out_valid(uio_out[3])
  );

  // List all unused inputs to prevent warnings
  wire _unused = &{uio_in[7:2], ena, 1'b0};

endmodule
