`default_nettype none

module fir_filter #(
    parameter Taps = 16
) (
    input wire clk,
    input wire rst_n,
    input wire signed [15:0] din,
    input wire mode,
    input wire in_valid,
    input wire out_ready,

    output wire signed [15:0] dout,
    output wire out_valid,
    output wire in_ready
);

  localparam SampleWidth = 16;
  localparam CoeffWidth = 16;
  // AccWidth depends on output width from trunc_mult 
  localparam AccWidth = ((SampleWidth + CoeffWidth) - (CoeffWidth - 1)) + $clog2(Taps);

  assign out_valid = (curr_st == Done);
  assign in_ready  = (curr_st == Ready);

  wire out_handshake, in_handshake;
  assign out_handshake = out_ready && out_valid;
  assign in_handshake  = in_ready && in_valid;

  wire mac_cnt_full;
  assign mac_cnt_full = {1'b0, mac_idx} == Taps[$clog2(Taps):0] - 1'b1;

  assign dout = acc[15:0];

  localparam [2:0] Idle = 3'b000, Ready = 3'b010, Compute = 3'b011, Done = 3'b100;
  reg [2:0] curr_st, next_st;

  // state machine
  always @(posedge clk or negedge rst_n) begin : reg_curr_state
    if (~rst_n) begin
      curr_st <= Idle;
    end else begin
      curr_st <= next_st;
    end
  end

  // next state
  always @(*) begin : comb_next_state
    next_st = curr_st;
    case (curr_st)
      Idle: begin
        next_st = Ready;
      end
      Ready: begin
        if (in_handshake && ~mode) begin
          next_st = Compute;
        end else if (in_handshake && mode) begin
          next_st = Done;  // coeff loaded, no output to show
        end
      end
      Compute: begin
        if (mac_cnt_full) begin
          next_st = Done;
        end
      end
      Done: begin
        if (out_handshake) begin
          next_st = Ready;
        end
      end
      default: begin
        next_st = Idle;
      end
    endcase
  end

  reg signed [CoeffWidth-1:0] coeff[0:Taps-1];
  integer c_idx;
  always @(posedge clk or negedge rst_n) begin : shift_reg_coeff_line
    if (~rst_n) begin
      for (c_idx = 0; c_idx < Taps; c_idx++) begin
        coeff[c_idx] <= 0;
      end
    end else if (in_handshake && mode) begin
      coeff[0] <= din;

      for (c_idx = 1; c_idx < Taps; c_idx++) begin
        coeff[c_idx] <= coeff[c_idx-1];
      end
    end
  end

  reg signed [SampleWidth-1:0] samples[0:Taps-1];
  integer s_idx;
  always @(posedge clk or negedge rst_n) begin : shift_reg_sample_line
    if (~rst_n) begin
      for (s_idx = 0; s_idx < Taps; s_idx++) begin
        samples[s_idx] <= 0;
      end
    end else if (in_handshake && ~mode) begin
      samples[0] <= din;

      for (s_idx = 1; s_idx < Taps; s_idx++) begin
        samples[s_idx] <= samples[s_idx-1];
      end
    end
  end

  reg [$clog2(Taps)-1:0] mac_idx;
  always @(posedge clk or negedge rst_n) begin : mac_idx_counter
    if (~rst_n) begin
      mac_idx <= 0;
    end else if (curr_st == Compute) begin
      mac_idx <= mac_idx + 1'b1;
    end else if (curr_st != Compute) begin
      mac_idx <= 0;
    end
  end

  reg signed [AccWidth-1:0] acc;
  always @(posedge clk or negedge rst_n) begin : reg_mac_accumulator
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

endmodule
