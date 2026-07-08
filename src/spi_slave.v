`default_nettype none

module spi_slave (
    input  wire sclk,
    //input  wire rst_n,
    input  wire cs_n,
    input  wire mosi,
    output wire miso
);

  // switch this to oversampling man this is terrible.......
  // dont do the cdc bullshit please switch to oversampling

  // spi mode 0

  assign miso = (~cs_n) ? tx_byte[7] : 1'bz;

  reg [7:0] rx_byte, tx_byte;
  reg [3:0] bit_cnt;

  always @(posedge sclk or posedge cs_n) begin
    if (cs_n) begin
      rx_byte <= 0;
    end else begin
      rx_byte <= {rx_byte[6:0], mosi};
    end
  end

  always @(posedge sclk or posedge cs_n) begin
    if (cs_n) begin
      bit_cnt <= 0;
    end else if (bit_cnt == 4'd8) begin
      bit_cnt <= 0;
    end else begin
      bit_cnt <= bit_cnt + 1'b1;
    end
  end

  always @(negedge sclk or posedge cs_n) begin
    if (cs_n) begin
      tx_byte <= 8'h5C;
    end else begin
      tx_byte <= {tx_byte[6:0], 1'b0};
    end
  end

endmodule
