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
  localparam AccWidth = ((SampleWidth + CoeffWidth) - (CoeffWidth - 1)) + $clog2(Taps);
  //localparam AccWidth = SampleWidth + CoeffWidth + $clog2(Taps);
  localparam OutBytes = SampleWidth / 8;
  localparam OutCntWidth = OutBytes <= 1 ? 1 : $clog2(OutBytes);

  assign out_valid = (curr_st == Done);
  assign in_ready  = (curr_st == Ready) || (curr_st == LoadCoeff);

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

  always @(*) begin
    next_st = curr_st;
    case (curr_st)
      Idle: begin
        if (load) begin
          next_st = LoadCoeff;
        end else if (in_valid && in_ready && !load) begin
          next_st = Compute;
        end
      end
      LoadCoeff: begin  // might need to add byte_en here, should be fine?
        if (load) begin
          next_st = LoadCoeff;
        end else begin
          next_st = Ready;
        end
      end
      Ready: begin
        if (in_valid && byte_en) begin
          next_st = Compute;
        end else if (load) begin
          next_st = LoadCoeff;
        end
      end
      Compute: begin
        if (load) begin
          next_st = LoadCoeff;
        end else if ({1'b0, mac_idx} == Taps[$clog2(Taps):0] - 1'b1) begin  // linter approved :)
          next_st = Done;
        end
      end
      Done: begin
        if ({1'b0, out_byte_cnt} == OutBytes[$clog2(OutBytes):0] - 1'b1) begin
          next_st = Ready;
        end
      end
      default: begin
        next_st = Idle;
      end
    endcase
  end

  reg signed [AccWidth-1:0] acc;
  reg signed [SampleWidth-1:0] samples[0:Taps-1];
  reg signed [CoeffWidth-1:0] coeff[0:Taps-1];
  reg signed [(SampleWidth/2)-1:0] low_byte_buf;

  reg [$clog2(Taps)-1:0] mac_idx;
  reg [$clog2(Taps)-1:0] coeff_idx;
  reg [OutCntWidth-1:0] out_byte_cnt;

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      low_byte_buf <= 0;
    end else if ((curr_st == LoadCoeff && !byte_en) || (curr_st == Ready && !byte_en)) begin
      low_byte_buf <= din;
    end else begin
      low_byte_buf <= 0;
    end
  end

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      coeff_idx <= 0;
    end else if (curr_st != LoadCoeff) begin
      coeff_idx <= 0;
    end else if (curr_st == LoadCoeff && in_valid && byte_en) begin
      coeff_idx <= coeff_idx + 1'b1;
    end
  end

  // coeff loading
  integer k;
  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      for (k = 0; k < Taps; k = k + 1) begin
        coeff[k] <= 0;
      end
    end else if (curr_st == LoadCoeff && in_valid && byte_en) begin
      coeff[coeff_idx] <= {din, low_byte_buf};
    end
  end

  integer i;
  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      for (i = 0; i < Taps; i = i + 1) begin
        samples[i] <= 0;
      end
    end else if (curr_st == Ready) begin
      if (in_valid && byte_en) begin
        samples[0] <= {din, low_byte_buf};
      end else if (!in_valid) begin
        for (i = 1; i < Taps; i = i + 1) begin
          samples[i] <= samples[i-1];
        end
      end
    end
  end

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      mac_idx <= 0;
    end else if (curr_st == Done) begin
      mac_idx <= 0;
    end else if (curr_st == Compute) begin
      mac_idx <= mac_idx + 1'b1;
    end
  end

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      acc <= 0;
    end else if (curr_st == Ready) begin
      acc <= 0;
    end else if (curr_st == Compute) begin
      //acc <= acc + (coeff[mac_idx] * samples[mac_idx]);
      acc <= acc + out;
    end
  end

  reg signed [16:0] out;
  trunc_mult #(
      .DataWidth(SampleWidth),
      .DropBits (CoeffWidth - 1)
  ) mult (
      .a  (samples[mac_idx]),
      .b  (coeff[mac_idx]),
      .out(out)
  );

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      out_byte_cnt <= 0;
    end else if (curr_st == Done && out_ready) begin
      out_byte_cnt <= out_byte_cnt + 1'b1;
    end else if (curr_st != Done) begin
      out_byte_cnt <= 0;
    end
  end

  // low then high byte on output
  // assign dout = acc[(out_byte_cnt*8)+(CoeffWidth-1)+:8];

  assign dout = acc[(out_byte_cnt*8)+:8];

endmodule
