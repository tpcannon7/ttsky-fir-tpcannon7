`default_nettype none

module fir_filter #(
    parameter Taps = 36
) (
    input wire clk,
    input wire rst_n,
    input wire signed [11:0] din,
    input wire mode,  // FIR mode; ModeSample = 1, ModeCoeff = 0
    input wire in_valid,
    input wire out_ready,

    output wire signed [11:0] dout,
    output wire out_valid,
    output wire in_ready
);

  localparam SampleWidth = 12;
  localparam CoeffWidth = 12;
  localparam DropBits = 8;
  localparam TruncOutWidth = (SampleWidth * 2) - DropBits;
  localparam CoeffFracBits = CoeffWidth - 1;
  localparam OutputWidth = 12;
  // AccWidth depends on output width from trunc_mult 
  localparam AccWidth = ((SampleWidth + CoeffWidth) - DropBits) + $clog2(Taps);

  localparam ModeSample = 1'b1;
  localparam ModeCoeff = 1'b0;

  assign out_valid = (curr_st == Done);
  assign in_ready  = (curr_st == Ready);

  wire out_handshake, in_handshake;
  assign out_handshake = out_ready && out_valid;
  assign in_handshake  = in_ready && in_valid;

  wire mac_cnt_full;
  assign mac_cnt_full = {1'b0, mac_idx} == Taps[$clog2(Taps):0] - 1'b1;

  localparam OutLsb = CoeffFracBits - DropBits;
  localparam OutMsb = OutLsb + 11;
  localparam GuardBits = AccWidth - OutputWidth - (CoeffFracBits - DropBits);

  wire [11:0] output_slice;
  assign output_slice = acc[OutLsb+:12];

  // if bits in the accumulator above our 12 bit output slice don't match to our output slice sign bit
  // we know we have overflowed out of the 12 bit output slice result
  wire overflow;
  assign overflow = (acc[AccWidth-1:OutMsb+1] != {GuardBits{acc[OutMsb]}});

  // clamp our output
  assign dout = (overflow &  ~acc[AccWidth-1])  ? 12'h7FF :
                (overflow & acc[AccWidth-1])  ? 12'h800 :
                output_slice;

  localparam [1:0] Ready = 2'b00, Compute = 2'b01, Done = 2'b10;
  reg [1:0] curr_st, next_st;

  // state machine
  always @(posedge clk or negedge rst_n) begin : reg_curr_state
    if (~rst_n) begin
      curr_st <= Ready;
    end else begin
      curr_st <= next_st;
    end
  end

  // next state
  always @(*) begin : comb_next_state
    next_st = curr_st;
    case (curr_st)
      Ready: begin
        if (in_handshake && mode == ModeSample) begin
          next_st = Compute;
        end else if (in_handshake && mode == ModeCoeff) begin
          next_st = Done;  // coeff loaded, no output to show
        end
      end
      Compute: begin
        if (mac_cnt_full && mac_busy) begin
          next_st = Done;
        end
      end
      Done: begin
        if (out_handshake) begin
          next_st = Ready;
        end
      end
      default: begin
        next_st = Ready;
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
    end else if (in_handshake && mode == ModeCoeff) begin
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
    end else if (in_handshake && mode == ModeSample) begin
      samples[0] <= din;

      for (s_idx = 1; s_idx < Taps; s_idx++) begin
        samples[s_idx] <= samples[s_idx-1];
      end
    end
  end

  reg [$clog2(Taps)-1:0] mac_idx;
  reg mac_busy;
  reg signed [11:0] curr_sample, curr_coeff;
  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      mac_busy <= 1'b0;
      curr_sample <= 0;
      curr_coeff <= 0;
      mac_idx <= 0;
    end else if (curr_st != Compute) begin
      mac_busy <= 1'b0;
      curr_coeff <= 0;
      curr_sample <= 0;
      mac_idx <= 0;
    end else if (curr_st == Compute && mac_busy == 1'b0) begin
      mac_busy <= 1'b1;
      curr_coeff <= coeff[mac_idx];
      curr_sample <= samples[mac_idx];
    end else if (curr_st == Compute && !mac_cnt_full && mac_busy == 1'b1) begin
      mac_busy <= ~mac_busy;
      mac_idx  <= mac_idx + 1'b1;
    end
  end

  reg signed [AccWidth-1:0] acc;
  always @(posedge clk or negedge rst_n) begin : reg_mac_accumulator
    if (~rst_n) begin
      acc <= 0;
    end else if (curr_st != Compute && curr_st != Done) begin
      acc <= 0;
    end else if (curr_st == Compute && mac_busy == 1'b1) begin
      acc <= acc + {{AccWidth - TruncOutWidth{trunc_out[TruncOutWidth-1]}}, trunc_out};
    end
  end

  wire signed [TruncOutWidth-1:0] trunc_out;
  trunc_mult #(
      .DataWidth(SampleWidth),
      .DropBits (DropBits)
  ) mult (
      .a  (curr_sample),
      .b  (curr_coeff),
      .out(trunc_out)
  );

endmodule

`default_nettype wire
