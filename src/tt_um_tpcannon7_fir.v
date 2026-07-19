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
  assign uio_out[7:3] = 0;
  assign uio_out[1:0] = 0;
  assign uio_oe = 8'b00000100;
  assign uo_out = 8'b00000000;

  wire [11:0] spi_tx_data, spi_rx_data;
  wire spi_curr_frame_fir_mode, spi_rx_valid;
  wire control_curr_frame_mode;

  spi spi (
      .clk(clk),
      .rst_n(rst_n),
      .cs_n(uio_in[0]),
      .mosi(uio_in[1]),
      .miso(uio_out[2]),
      .sclk(uio_in[3]),
      .fir_mode(ui_in[0]),
      .rx_data_out(spi_rx_data),
      .tx_data_in(spi_tx_data),
      .curr_frame_fir_mode(spi_curr_frame_fir_mode),
      .spi_rx_valid(spi_rx_valid)
  );

  wire [11:0] filter_in, filter_out;

  control control (
      .clk(clk),
      .rst_n(rst_n),
      .spi_rx_data(spi_rx_data),
      .spi_tx_data(spi_tx_data),
      .dout_fir(filter_out),
      .din_fir(filter_in),
      .spi_rx_valid(spi_rx_valid),
      .spi_curr_frame_fir_mode(spi_curr_frame_fir_mode),
      .fir_out_valid(fir_out_valid),
      .control_out_ready(control_out_ready),
      .fir_in_ready(fir_in_ready),
      .control_in_valid(control_in_valid),
      .control_curr_frame_fir_mode(control_curr_frame_mode)
  );

  wire fir_in_ready, fir_out_valid;
  wire control_in_valid, control_out_ready;

  fir_filter #(
      .Taps(28)
  ) fir (
      .clk(clk),
      .rst_n(rst_n),
      .din(filter_in),
      .dout(filter_out),
      .mode(control_curr_frame_mode),
      .in_valid(control_in_valid),
      .out_ready(control_out_ready),
      .in_ready(fir_in_ready),
      .out_valid(fir_out_valid)
  );

  // List all unused inputs to prevent warnings
  wire _unused = &{uio_in[7:4], uio_in[2], ui_in[7:1], ena, 1'b0};

endmodule
