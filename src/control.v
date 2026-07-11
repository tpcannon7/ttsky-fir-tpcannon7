`default_nettype none

module control (
    input wire clk,
    input wire rst_n,

    input wire [15:0] spi_rx_data,
    output wire [15:0] spi_tx_data,
    input wire spi_done,
    input wire spi_curr_frame_mode,

    input wire [15:0] dout_fir,
    output wire [15:0] din_fir,
    input wire fir_out_valid,
    output wire control_out_ready,
    input wire fir_in_ready,
    output wire control_in_valid
);

  localparam [2:0] Idle = 3'b000, SpiRx = 3'b001, FirOutput = 3'b010;
  reg [2:0] curr_st, next_st;

  assign control_in_valid  = (curr_st == SpiRx);
  assign control_out_ready = (curr_st == FirOutput);

  wire fir_control_in_handshake, fir_control_out_handshake;
  assign fir_control_in_handshake  = control_in_valid && fir_in_ready;
  assign fir_control_out_handshake = control_out_ready && fir_out_valid;

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      curr_st <= Idle;
    end else begin
      curr_st <= next_st;
    end
  end

  always @(*) begin
    next_st = curr_st;
    case (curr_st)
      Idle: begin
        if (spi_done) begin
          next_st = SpiRx;
        end
      end
      SpiRx: begin
        if (fir_control_in_handshake) begin
          next_st = FirOutput;
        end
      end
      FirOutput: begin
        if (fir_control_out_handshake) begin
          next_st = Idle;
        end
      end
      default: next_st = curr_st;
    endcase
  end

  reg [15:0] filter_out_buf, spi_in_buf;

  assign din_fir = spi_in_buf;

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      spi_in_buf <= 0;
    end else if (curr_st == SpiRx) begin
      spi_in_buf <= spi_rx_data;
    end
  end

  assign spi_tx_data = filter_out_buf;

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      filter_out_buf <= 0;
    end else if (curr_st == FirOutput && fir_control_out_handshake) begin
      filter_out_buf <= dout_fir;
    end
  end


endmodule
