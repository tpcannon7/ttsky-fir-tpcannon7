`default_nettype none

module spi_slave (
    input wire clk,
    input wire rst_n,

    // spi signals
    input  wire sclk,
    input  wire mosi,
    input  wire cs_n,
    output wire miso,

    // internal transfer
    input  wire [7:0] tx_byte,
    output wire [7:0] rx_byte
);

  wire sclk_rising, cs_n_rising;
  wire sclk_falling, cs_n_falling;

  assign sclk_rising  = (sclk_sync[1] == 1'b1) && (sclk_sync[2] == 1'b0);
  assign sclk_falling = (sclk_sync[1] == 1'b0) && (sclk_sync[2] == 1'b1);

  assign cs_n_rising  = (cs_n_sync[1] == 1'b1) && (cs_n_sync[2] == 1'b0);
  assign cs_n_falling = (cs_n_sync[1] == 1'b0) && (cs_n_sync[2] == 1'b1);

  reg [2:0] sclk_sync, mosi_sync, cs_n_sync;

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      sclk_sync <= 0;
      mosi_sync <= 0;
      cs_n_sync <= 0;
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
    end
  end

  localparam [1:0] Idle = 2'b00, Busy = 2'b01, Done = 2'b10;
  reg [1:0] curr_st, next_st;

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
        if (bit_cnt == 3'd7) begin
          next_st = Done;
        end
      end
      Done: begin
        if (cs_n_rising) begin
          next_st = Idle;
        end
      end
      default: next_st = curr_st;
    endcase
  end


  reg [7:0] rx_buf, tx_buf;
  reg [2:0] bit_cnt;

  assign miso = (~cs_n) ? tx_buf[7] : 1'bz;

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      rx_buf <= 0;
    end else if (curr_st == Busy && sclk_rising) begin
      rx_buf <= {rx_buf[6:0], mosi};
    end else if (curr_st == Done) begin
      rx_buf <= 0;
    end
  end

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      bit_cnt <= 0;
    end else if (curr_st == Busy && sclk_rising) begin
      bit_cnt <= bit_cnt + 1'b1;
    end else if (bit_cnt == 3'd7) begin
      bit_cnt <= 0;
    end
  end

  always @(negedge clk or negedge rst_n) begin
    if (~rst_n) begin
      tx_buf <= 0;
    end else if (curr_st == Busy && sclk_falling) begin
      tx_buf <= {tx_buf[6:0], 1'b0};
    end else if (curr_st == Done) begin
      tx_buf <= tx_byte;
    end
  end

  reg [7:0] last_rx;

  assign rx_byte = last_rx;

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      last_rx <= 0;
    end else if (curr_st == Done) begin
      last_rx <= rx_buf;
    end
  end

endmodule
