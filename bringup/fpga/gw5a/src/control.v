`default_nettype none

module control (
    input wire clk,
    input wire rst_n,

    input wire [11:0] spi_rx_data,
    output wire [11:0] spi_tx_data,
    input wire spi_rx_valid,
    input wire spi_curr_frame_fir_mode,

    input wire [11:0] dout_fir,
    output wire [11:0] din_fir,
    input wire fir_out_valid,
    output wire control_out_ready,
    input wire fir_in_ready,
    output wire control_in_valid,
    output wire control_curr_frame_fir_mode
);

  assign control_in_valid  = rx_valid_reg;
  assign control_out_ready = 1'b1;

  wire fir_control_in_handshake, fir_control_out_handshake;
  assign fir_control_in_handshake  = control_in_valid && fir_in_ready;
  assign fir_control_out_handshake = control_out_ready && fir_out_valid;

  reg [11:0] filter_out_buf, spi_in_buf;
  reg curr_frame_fir_mode;
  reg rx_valid_reg;

  assign din_fir = spi_in_buf;
  assign control_curr_frame_fir_mode = curr_frame_fir_mode;

  always @(posedge clk or negedge rst_n) begin : reg_spi_rx_data
    if (~rst_n) begin
      spi_in_buf <= 0;
      rx_valid_reg <= 1'b0;
      curr_frame_fir_mode <= 1'b0;
    end else if (spi_rx_valid) begin
      spi_in_buf <= spi_rx_data;
      rx_valid_reg <= 1'b1;
      curr_frame_fir_mode <= spi_curr_frame_fir_mode;
    end else if (fir_control_in_handshake) begin
      rx_valid_reg <= 1'b0;
    end
  end

  assign spi_tx_data = filter_out_buf;

  always @(posedge clk or negedge rst_n) begin : reg_fir_output
    if (~rst_n) begin
      filter_out_buf <= 0;
    end else if (fir_control_out_handshake) begin
      filter_out_buf <= dout_fir;
    end
  end

endmodule

`default_nettype wire
