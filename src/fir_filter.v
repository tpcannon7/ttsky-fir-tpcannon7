`default_nettype none

module fir_filter #(
    parameter Taps = 8
) (
    input wire clk,
    input wire rst_n,
    input wire signed [7:0] din,
    input wire load,
    input wire in_valid,

    output wire signed [7:0] dout,
    output wire out_valid,
    output wire in_ready
);

  localparam SampleWidth = 8;
  localparam CoeffWidth = 8;
  localparam OutWidth = SampleWidth + CoeffWidth + $clog2(Taps);

  /* verilator lint_off WIDTHEXPAND */
  assign out_valid = (curr_st == Compute) && (mac_idx == Taps - 1);
  /* verilator lint_on WIDTHEXPAND */
  assign in_ready  = (curr_st == Ready);

  localparam [1:0] Idle = 2'b00, LoadCoeff = 2'b01, Ready = 2'b10, Compute = 2'b11;
  reg [1:0] curr_st, next_st;

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
      LoadCoeff: begin
        if (load) begin
          next_st = LoadCoeff;
        end else begin
          next_st = Ready;
        end
      end
      Ready: begin
        if (in_valid) begin
          next_st = Compute;
        end else if (load) begin
          next_st = LoadCoeff;
        end
      end
      Compute: begin
        if (load) begin
          next_st = LoadCoeff;
        end else if (out_valid) begin
          next_st = Ready;
        end
      end
      default: begin
        next_st = Idle;
      end
    endcase
  end

  reg signed [OutWidth-1:0] acc;
  reg signed [SampleWidth-1:0] samples[0:Taps-1];
  reg signed [CoeffWidth-1:0] coeff[0:Taps-1];
  reg [$clog2(Taps)-1:0] mac_idx;
  reg [$clog2(Taps)-1:0] coeff_idx;

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      coeff_idx <= 0;
    end else if (curr_st != LoadCoeff) begin
      coeff_idx <= 0;
    end else begin
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
    end else if (curr_st == LoadCoeff) begin
      coeff[coeff_idx] <= din;
    end
  end

  // load incoming sample
  integer i;
  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      for (i = 0; i < Taps; i = i + 1) begin
        samples[i] <= 0;
      end
    end else if (curr_st == Ready && in_valid) begin
      samples[0] <= din;
      for (i = 1; i < Taps; i = i + 1) begin
        samples[i] <= samples[i-1];
      end
    end
  end

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      mac_idx <= 0;
    end else if (curr_st == Ready) begin
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
      acc <= acc + (coeff[mac_idx] * samples[mac_idx]);
    end
  end

  // TODO: change to correct bit slice
  assign dout = acc[14:7];

endmodule
