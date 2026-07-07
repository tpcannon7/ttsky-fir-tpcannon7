`default_nettype none

module spi (
    input  wire sclk,
    input  wire rst_n,
    input  wire cs_n,
    input  wire mosi,
    output wire miso,

    input  wire [15:0] word_in,
    output wire [15:0] word_out
);

  // SPI mode 0 btw

  localparam [1:0] Idle = 2'b00, Busy = 2'b01, Done = 2'b10;
  reg [1:0] curr_st, next_st;

  always @(posedge sclk or negedge rst_n) begin
    if (~rst_n) begin
      curr_st <= Idle;
    end else begin
      curr_st <= next_st;
    end
  end

  always @(*) begin
    next_st = curr_st;
    case (curr_st)
      Idle: if (~cs_n) next_st = Busy;
      Busy: if (bit_cnt == 7) next_st = Done;
      Done: begin
        if (~cs_n) begin
          next_st = Busy;
        end else begin
          next_st = Idle;
        end
      end
      default: next_st = Idle;
    endcase
  end

  reg [7:0] shift_in;
  reg [2:0] bit_cnt;

  reg [7:0] shift_out;
  assign miso = shift_out[7];

  always @(posedge sclk or negedge rst_n) begin : shift_mosi_in
    if (~rst_n) begin
      shift_in <= 0;
    end else if (curr_st == Busy) begin
      shift_in <= {shift_in[6:0], mosi};
    end
  end

  always @(negedge sclk or negedge rst_n) begin : shift_miso_out
    if (~rst_n) begin
      shift_out <= 0;
    end else if (curr_st == Busy) begin
      shift_out <= {shift_out[6:0], 1'b0};
    end else if (curr_st == Done) begin
      shift_out <= shift_in;  // change later PLEASE
    end
  end

  always @(posedge sclk or negedge rst_n) begin : bit_counter
    if (~rst_n) begin
      bit_cnt <= 0;
    end else if (curr_st == Busy) begin
      bit_cnt <= bit_cnt + 1'b1;
    end else if (bit_cnt == 7) begin
      bit_cnt <= 0;
    end
  end

endmodule
