`default_nettype none

module fir_filter #(
    parameter Taps = 8
) (
    input wire clk,
    input wire rst_n,
    input wire signed [7:0] din,
    input wire load,
    input wire in_valid,
    input wire out_ready,
    input wire byte_en,

    output wire signed [7:0] dout,
    output wire out_valid,
    output wire in_ready
);

  localparam SampleWidth = 16;
  localparam CoeffWidth = 16;
  localparam OutBytes = SampleWidth / 8;
  localparam OutCntWidth = OutBytes <= 1 ? 1 : $clog2(OutBytes);
  // AccWidth depends on output width from trunc_mult 
  localparam AccWidth = ((SampleWidth + CoeffWidth) - (CoeffWidth - 1)) + $clog2(Taps);

  assign out_valid = (curr_st == Done);
  assign in_ready  = (curr_st == Ready) || (curr_st == LoadCoeff);

  wire out_handshake, in_handshake;
  assign out_handshake = out_ready && out_valid;
  assign in_handshake  = in_ready && in_valid;

  wire mac_cnt_full, out_byte_cnt_full, coeff_idx_full;
  assign mac_cnt_full = {1'b0, mac_idx} == Taps[$clog2(Taps):0] - 1'b1;
  assign out_byte_cnt_full = {1'b0, out_byte_cnt} == OutBytes[$clog2(OutBytes):0] - 1'b1;
  assign coeff_idx_full = {1'b0, coeff_idx} == Taps[$clog2(Taps):0] - 1'b1;

  assign dout = acc[(out_byte_cnt*8)+:8];

  localparam [2:0] Idle = 3'b000, LoadCoeff = 3'b001, Ready = 3'b010, Compute = 3'b011, Done = 3'b100;
  reg [2:0] curr_st, next_st;

  // state machine
  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      curr_st <= Idle;
    end else begin
      curr_st <= next_st;
    end
  end

  // next state
  always @(*) begin
    next_st = curr_st;
    case (curr_st)
      Idle: begin
        if (load) begin
          next_st = LoadCoeff;
        end
      end
      LoadCoeff: begin
        if (load) begin
          next_st = LoadCoeff;
        end else begin
          next_st = Ready;
        end
      end
      Ready: begin
        if (in_handshake && byte_en) begin
          next_st = Compute;
        end else if (load) begin
          next_st = LoadCoeff;
        end
      end
      Compute: begin
        if (mac_cnt_full) begin
          next_st = Done;
        end
      end
      Done: begin
        if (out_byte_cnt_full && out_handshake) begin
          next_st = Ready;
        end
      end
      default: begin
        next_st = Idle;
      end
    endcase
  end

  reg signed [(SampleWidth/2)-1:0] low_byte_buf;
  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      low_byte_buf <= 0;
    end else if (in_handshake && !byte_en) begin
      low_byte_buf <= din;
    end
  end

  reg [$clog2(Taps)-1:0] coeff_idx;
  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      coeff_idx <= 0;
    end else if (curr_st == LoadCoeff) begin
      if (in_handshake && byte_en && !coeff_idx_full) begin
        coeff_idx <= coeff_idx + 1'b1;
      end
    end else if (curr_st != LoadCoeff) begin
      coeff_idx <= 0;
    end
  end

  reg signed [CoeffWidth-1:0] coeff[0:Taps-1];
  integer idx;
  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      for (idx = 0; idx < Taps; idx++) begin
        coeff[idx] <= 0;
      end
    end else if (curr_st == LoadCoeff) begin
      if (in_handshake && byte_en) begin
        coeff[coeff_idx] <= {din, low_byte_buf};
      end
    end
  end

  reg signed [SampleWidth-1:0] samples[0:Taps-1];
  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      for (idx = 0; idx < Taps; idx++) begin
        samples[idx] <= 0;
      end
    end else if (curr_st == Ready) begin
      if (in_handshake && byte_en) begin
        samples[0] <= {din, low_byte_buf};

        for (idx = 1; idx < Taps; idx++) begin
          samples[idx] <= samples[idx-1];
        end
      end
    end
  end

  reg [$clog2(Taps)-1:0] mac_idx;
  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      mac_idx <= 0;
    end else if (curr_st == Compute) begin
      mac_idx <= mac_idx + 1'b1;
    end else if (curr_st != Compute) begin
      mac_idx <= 0;
    end
  end

  reg signed [AccWidth-1:0] acc;
  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      acc <= 0;
    end else if (curr_st != Compute && curr_st != Done) begin
      acc <= 0;
    end else if (curr_st == Compute) begin
      acc <= acc + {3'b111, trunc_out};
    end
  end

  wire signed [16:0] trunc_out;
  trunc_mult #(
      .DataWidth(SampleWidth),
      .DropBits (CoeffWidth - 1)
  ) mult (
      .a  (samples[mac_idx]),
      .b  (coeff[mac_idx]),
      .out(trunc_out)
  );

  reg [OutCntWidth-1:0] out_byte_cnt;
  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      out_byte_cnt <= 0;
    end else if (curr_st == Done && out_handshake && !out_byte_cnt_full) begin
      out_byte_cnt <= out_byte_cnt + 1'b1;
    end else if (curr_st != Done) begin
      out_byte_cnt <= 0;
    end
  end

endmodule
