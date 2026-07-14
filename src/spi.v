`default_nettype none

module spi (
    input wire clk,
    input wire rst_n,

    // spi signals
    input  wire sclk,
    input  wire mosi,
    input  wire cs_n,
    output wire miso,

    input wire mode,

    // internal transfer
    input wire [11:0] tx_data_in,
    output wire [11:0] rx_data_out,
    output wire spi_rx_valid,
    output wire curr_frame_mode
);

  localparam SpiFrameWidth = 16;

  wire sclk_rising;
  /* verilator lint_off UNUSEDSIGNAL */
  wire cs_n_rising;
  /* verilator lint_on UNUSEDSIGNAL */
  wire sclk_falling, cs_n_falling;

  assign sclk_rising  = (sclk_sync[1] == 1'b1) && (sclk_sync[2] == 1'b0);
  assign sclk_falling = (sclk_sync[1] == 1'b0) && (sclk_sync[2] == 1'b1);

  assign cs_n_rising  = (cs_n_sync[1] == 1'b1) && (cs_n_sync[2] == 1'b0);
  assign cs_n_falling = (cs_n_sync[1] == 1'b0) && (cs_n_sync[2] == 1'b1);

  // new "mode" pin will function as: LOW == coeff frame, HIGH == sample frame
  // we will idle the mode pin at high (default samples), coeff loading is pulling low as
  // a special case

  reg [2:0] sclk_sync, cs_n_sync, mode_sync;
  /* verilator lint_off UNUSEDSIGNAL */
  reg [2:0] mosi_sync;
  /* verilator lint_on UNUSEDSIGNAL */

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      sclk_sync <= 3'b000;
      mosi_sync <= 3'b000;
      cs_n_sync <= 3'b111;
      mode_sync <= 3'b111;
    end else begin
      sclk_sync[0] <= sclk;
      sclk_sync[1] <= sclk_sync[0];
      sclk_sync[2] <= sclk_sync[1];

      mosi_sync[0] <= mosi;
      mosi_sync[1] <= mosi_sync[0];
      mosi_sync[2] <= mosi_sync[1];

      cs_n_sync[0] <= cs_n;
      cs_n_sync[1] <= cs_n_sync[0];
      cs_n_sync[2] <= cs_n_sync[1];

      mode_sync[0] <= mode;
      mode_sync[1] <= mode_sync[0];
      mode_sync[2] <= mode_sync[1];
    end
  end

  localparam [1:0] Idle = 2'b00, Busy = 2'b01, Done = 2'b10;
  reg [1:0] curr_st, next_st;

  assign spi_rx_valid = (curr_st == Done);
  assign curr_frame_mode = curr_frame_mode_reg;

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
        if (cs_n_falling) begin
          next_st = Busy;
        end
      end
      Busy: begin
        if (bit_cnt == (SpiFrameWidth)) begin
          next_st = Done;
        end else if (cs_n_rising) begin
          next_st = Idle;  // erroneous cs_n HIGH during transcation
        end
      end
      Done: begin
        next_st = Idle;
      end
      default: next_st = curr_st;
    endcase
  end

  reg [SpiFrameWidth-1:0] rx_buf, tx_buf;
  // bit count needs to hold 1-16 since we increment on first sclk cycle from 
  // 0-1 and miss the final bit if we count to 15 (only 14 bits with counter 1-15)
  reg [$clog2(SpiFrameWidth):0] bit_cnt;
  reg curr_frame_mode_reg;

  assign miso = (~cs_n) ? tx_buf[SpiFrameWidth-1] : 1'bz;
  assign rx_data_out = rx_buf[15:4];

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      rx_buf <= 0;
    end else if (curr_st == Busy && sclk_rising) begin
      rx_buf <= {rx_buf[SpiFrameWidth-2:0], mosi};
    end else if (curr_st == Idle) begin
      rx_buf <= 0;
    end
  end

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      bit_cnt <= 0;
    end else if (curr_st == Busy && sclk_rising) begin
      bit_cnt <= bit_cnt + 1'b1;
    end else if (bit_cnt == (SpiFrameWidth)) begin
      bit_cnt <= 0;
    end else if (curr_st == Idle) begin
      bit_cnt <= 0;
    end
  end

  always @(negedge clk or negedge rst_n) begin
    if (~rst_n) begin
      tx_buf <= 0;
    end else if (curr_st == Busy && sclk_falling) begin
      tx_buf <= {tx_buf[SpiFrameWidth-2:0], 1'b0};
    end else if (cs_n_falling) begin
      tx_buf <= {tx_data_in, 4'b0000};  // pad to fit 16 bit frame
    end
  end

  assign curr_frame_mode = curr_frame_mode_reg;

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      curr_frame_mode_reg <= 0;
    end else if (bit_cnt == SpiFrameWidth) begin
      curr_frame_mode_reg <= mode_sync[2];
    end else if (curr_st == Idle) begin
      curr_frame_mode_reg <= 0;
    end
  end


endmodule
